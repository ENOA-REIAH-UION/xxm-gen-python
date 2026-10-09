#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小兮码字典配置生成
------------------------------------
功能概述：
    读取字根映射表、字符拆分表、无理码表、词语表等源文件，
    经过简码分配、冲突规避、词组编码生成等处理后，
    输出合并后的 Rime 字典文件：xxm.dict.yaml，
    同时导出一份完整的汉字全码表：qm.txt（便于调试与核对）

输入文件：
    keymap.txt     字根/笔画 -> 编码 的映射表
    info_new.txt   每个汉字的拼音、拆分字根、字频权重
    wlm.txt        无理码（单字自定义码）与多字词组
    dianer.txt     词语表（词、拼音、音节）

输出文件：
    qm.txt         汉字 -> 完整编码（5码）
    xxm.dict.yaml  最终合并字典
"""

from __future__ import annotations

import collections
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Set

KEYMAP_FILE = Path("keymap.txt")       # 字根映射表
INFO_NEW_FILE = Path("info_new.txt")   # 汉字拆分与字频
WLM_FILE = Path("wlm.txt")             # 无理码 + 多字词组
DIANER_FILE = Path("dianer.txt")       # 词语表

FULL_CODE_FILE = Path("qm.txt")        # 输出：汉字全码
XXM_FILE = Path("xxm.dict.yaml")       # 输出：合并字典

# 拼音首字母特殊映射：
# 韵母 a/e/o 统一映射到 r，zh 声母映射到 i
LSM = {"a": "r", "e": "r", "o": "r", "z": "i"}


# ----------------------------------------------------------------------
# 数据结构
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class CharInfo:
    """单个汉字的完整信息

    Attributes:
        char:      汉字本身
        pinyin:    拼音
        full_code: 完整 5 码编码
        weight:    字频权重（原脚本中的 zp 字段），如 "0.123"
    """
    char: str
    pinyin: str
    full_code: str
    weight: str


# ----------------------------------------------------------------------
# 通用工具函数
# ----------------------------------------------------------------------
def load_keymap(path: Path) -> Dict[Tuple[str, int], str]:
    """读取 keymap.txt，构建 (字根, 笔画数) -> 编码 的映射

    文件格式（制表符分隔）：
        字根 \t 编码 \t 笔画数
    """
    mapping: Dict[Tuple[str, int], str] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            my, aj, mw = line.split("\t")
            mapping[(my, int(mw))] = aj
    return mapping


def load_char_infos(
    path: Path,
    keymap: Dict[Tuple[str, int], str],
) -> Tuple[List[CharInfo], Dict[str, str]]:
    """读取 info_new.txt，构造每个汉字的完整编码信息

    文件格式（制表符分隔）：
        汉字 \t 拼音 \t 字根1 \t 字根2 \t 字根3 \t 字根4 \t 权重

    说明：
        编码由拼音首字母 + 4 段字根/笔画编码拼接而成，
        其中第二段按 2 画取码，第三、四段按 3 画取码，
        若按整段查不到则退化到按首字符查（兼容部分特殊字根）

    Returns:
        infos:       CharInfo 列表
        weight_map:  汉字 -> 权重 的映射
    """
    infos: List[CharInfo] = []
    weight_map: Dict[str, str] = {}

    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # 列顺序：汉字 拼音 字根1 字根2 字根3 字根4 权重
            z, y, c1, c2, c3, c4, zp = line.split("\t")

            m1 = y
            m2 = keymap[(c1, 2)]
            # 优先按整段 (c2, 3) 查表，否则退化到按首字符 (c2[0], 3)
            m3 = keymap.get((c2, 3), keymap[(c2[0], 3)])
            m4 = keymap.get((c3, 3), keymap[(c3[0], 3)])
            m5 = keymap[(c4, 3)]

            full_code = m1 + m2 + m3 + m4 + m5
            infos.append(CharInfo(z, y, full_code, zp))
            weight_map[z] = zp

    return infos, weight_map


def write_full_codes(infos: List[CharInfo], path: Path) -> None:
    """将每个汉字的完整编码写入 qm.txt，方便调试与核对"""
    with path.open("w", encoding="utf-8") as f:
        for ci in infos:
            f.write(f"{ci.char}\t{ci.full_code}\n")


def choose_prefix(
    full_code: str,
    occupied: Set[str],
    candidate_lengths: List[int],
) -> str:
    """从候选长度中依次截取前缀，返回第一个未被占用的编码

    Args:
        full_code:          完整编码
        occupied:           已被占用的编码集合
        candidate_lengths:  候选长度列表（按优先顺序）

    Returns:
        首个未被占用的前缀；若全部冲突则返回完整编码
    """
    for length in candidate_lengths:
        prefix = full_code[:length]
        if prefix not in occupied:
            return prefix
    return full_code


# ----------------------------------------------------------------------
# Rime 字典生成
# ----------------------------------------------------------------------
# 字典文件头部：包含元信息、编码器规则（不同字数使用不同取码公式）
XXM_HEADER = """# Rime dictionary: xxm
# encoding: utf-8

---
name: xxm
version: "0.6"
sort: original
columns:
  - text
  - code
  - stem
encoder:
  rules:
    - length_equal: 2
      formula: "AaAbAeBaBb"
    - length_equal: 3
      formula: "AaBaAcCaCb"
    - length_in_range: [4, 10]
      formula: "AaBaAdCaZa"
...
"""


def load_wlm(path: Path) -> Tuple[Dict[str, str], List[Tuple[str, str]]]:
    """读取 wlm.txt（无理码表）

    文件格式（制表符分隔）：
        字或词 \t 编码

    Returns:
        wlm_map: 单字 -> 编码（无理码）
        jianci:  多字词组列表 [(词, 编码), ...]
    """
    wlm_map: Dict[str, str] = {}
    jianci: List[Tuple[str, str]] = []

    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            char_or_word, code = line.split("\t")
            if len(char_or_word) == 1:
                wlm_map[char_or_word] = code
            else:
                jianci.append((char_or_word, code))

    return wlm_map, jianci


def generate_dict(
    char_infos: List[CharInfo],
    weight_map: Dict[str, str],
    wlm_map: Dict[str, str],
    jianci: List[Tuple[str, str]],
) -> None:
    """生成合并字典 xxm.dict.yaml

    生成顺序：
        1. wlm 中的多字词组
        2. wlm 中的单字（视为一种简码）
        3. 其余汉字的简码（2/3/4 码优先，避免冲突）
        4. wlm 单字的 4 码/全码补充映射
        5. dianer.txt 中的词组（按词长与阈值计算编码）
    """
    # 步骤 0：预处理
    # 汉字 -> [(拼音, 完整码), ...] 快速索引（同一汉字可能有多个读音）
    full_code_map: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for ci in char_infos:
        full_code_map[ci.char].append((ci.pinyin, ci.full_code))

    # 已占用的编码集合：用于简码分配时规避冲突
    bm: Set[str] = set()

    # 汉字 -> 该字所有可用简码（含无理码、简码、全码）
    # 例如 jm['重'] = {'cn', 'itaaa', 'ctaaa'}
    jm: Dict[str, Set[str]] = defaultdict(set)

    with XXM_FILE.open("w", encoding="utf-8") as f:
        # 文件头
        f.write(XXM_HEADER)

        # 步骤 1：写入 wlm 中的多字词组
        for phrase, code in jianci:
            if code.endswith("_"):
                # 以 "_" 结尾表示仅取编码首字（保留原有约定）
                f.write(f"{phrase}\t{code[0]}\n")
            else:
                f.write(f"{phrase}\t{code}\t72107210\n")
            bm.add(code)

        # 步骤 2：写入 wlm 中的单字（无理码，作为简码之一）
        for ch, code in wlm_map.items():
            f.write(f"{ch}\t{code}\t{code[:2]}0721\n")
            jm[ch].add(code)
            bm.add(code)

        # 步骤 3：为其余汉字分配简码
        for ci in char_infos:
            ch = ci.char
            if ch in wlm_map:
                continue  # 已在步骤 2 处理

            # 尝试 2/3/4 码前缀，取第一个未被占用的作为简码
            simple_code = choose_prefix(ci.full_code, bm, [2, 3, 4])
            bm.add(simple_code)

            jm[ch].add(simple_code)
            f.write(f"{ch}\t{simple_code}\t{simple_code[:2]}389\n")

        # 步骤 4：为 wlm 单字补充 4 码 / 全码映射
        # 目的：让无理码单字同时保留原编码的多种检索方式
        for ch, wlm_code in wlm_map.items():
            if ch not in full_code_map:
                continue

            for pinyin, full_code in full_code_map[ch]:
                prefix4 = full_code[:4]
                if prefix4 and prefix4 not in bm:
                    # 4 码不冲突：写入 4 码映射
                    f.write(f"{ch}\t{prefix4}\n")
                    f.write(f"{wlm_code}\t{prefix4}\n")
                    jm[ch].add(prefix4)
                else:
                    # 4 码冲突：退化为使用完整码
                    f.write(f"{ch}\t{full_code}\n")
                    f.write(f"{wlm_code}\t{full_code}\n")
                    jm[ch].add(full_code)

        # 将简码集合按长度升序排序，便于后续"取最短码"或"取首字母匹配的最短码"
        jm_sorted: Dict[str, List[str]] = {
            ch: sorted(codes, key=len) for ch, codes in jm.items()
        }

        # 步骤 5：处理 dianer.txt 中的词组
        with DIANER_FILE.open("r", encoding="utf-8") as dianer_f:
            for line in dianer_f:
                line = line.strip()
                if not line:
                    continue

                parts = line.split("\t")
                if len(parts) != 3:
                    continue

                w, _, y = parts
                yinjie = y.split(" ")

                # 计算每个字最短简码的总长度，作为是否造词的阈值
                try:
                    zmc = sum(len(jm_sorted[ch][0]) for ch in w)
                except KeyError:
                    # 有字符缺少简码，跳过该词
                    continue
                if zmc == 0:
                    continue

                # 为词中每个字生成候选码片段 cbm
                cbm: List[str] = []
                for idx, ch in enumerate(w):
                    if ch in wlm_map:
                        # 无理码单字：直接取其前两位
                        wlm_code = wlm_map[ch]
                        cbm.append(wlm_code[:2])
                        continue

                    yin = yinjie[idx] if idx < len(yinjie) else ""
                    # 音节首字母（含特殊映射：a/e/o->r, z->i）
                    first_letter = LSM.get(yin[:1].lower(), yin[:1].lower())

                    # 在所有首字母匹配的简码中，取最短的一条
                    matched = [c for c in jm_sorted[ch] if c[:1] == first_letter]
                    candidate = min(matched, key=len) if matched else jm_sorted[ch][0]

                    # 拼接：首字母 + 候选码第二个字符
                    if len(candidate) >= 2:
                        cbm.append(first_letter + candidate[1])
                    else:
                        cbm.append(candidate[:2])

                # 根据词长与阈值生成最终编码
                final_code = None
                if len(w) == 2 and zmc > 5:
                    # 二字词：码长 <=5 不造词，格式 xx9xx
                    final_code = f"{cbm[0]}9{cbm[1]}"
                elif len(w) == 3 and zmc > 6:
                    # 三字词：码长 <=6 不造词，格式 xx3xx
                    final_code = f"{cbm[0][0]}{cbm[1][0]}3{cbm[2]}"
                elif len(w) >= 4 and zmc > 0:
                    # 四字及以上：首字+次字+8+第三字+末字首
                    final_code = f"{cbm[0][0]}{cbm[1][0]}8{cbm[2][0]}{cbm[-1][0]}"

                if final_code:
                    f.write(f"{w}\t{final_code}\n")


# ----------------------------------------------------------------------
# 主入口
# ----------------------------------------------------------------------
def main() -> None:
    """主流程：读取源文件 -> 生成全码表 -> 生成合并字典"""
    # 1. 加载字根映射
    keymap = load_keymap(KEYMAP_FILE)

    # 2. 加载汉字拆分与字频
    char_infos, weight_map = load_char_infos(INFO_NEW_FILE, keymap)

    # 3. 导出全码表（调试用）
    write_full_codes(char_infos, FULL_CODE_FILE)

    # 4. 加载无理码与简词
    wlm_map, jianci = load_wlm(WLM_FILE)

    # 5. 生成合并字典
    generate_dict(char_infos, weight_map, wlm_map, jianci)


if __name__ == "__main__":
    main()