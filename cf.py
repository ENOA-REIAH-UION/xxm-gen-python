f=open('info.txt',encoding='utf-8',mode='r')
gb=[]
for line in f:
    z,y,b1,b2,b3,b4,g1,g2=line.strip('\r\n').split('\t')
    gb.append((z,y))
f.close()
f=open('keymap.txt',encoding='utf-8',mode='r')
zg2={}
zg3={}
for line in f:
    a,w,b=line.strip('\r\n').split('\t')
    if b=='2' and a[0] not in ['1','2','3','4','5']:
        zg2[a]=a
    elif b=='3' and a[0] not in ['1','2','3','4','5']:
        zg3[a]=a
f.close()
ty=[]
bs=[]
d={}
dt={}
f=open('cf.txt',encoding='utf-8',mode='r')
for line in f:
    z,tygf,chai,kind,length,tags,jg,kb=line.strip('\r\n').split('\t')
    if kb=='0':
        ch=list(chai.split(' '))
        if len(ch)==2:
            bq={'0':ch[0],'1':ch[1]}
        elif len(ch)==3 and tags=='':
            bq={'0':ch[0],'10':ch[1],'11':ch[2]}
        elif len(ch)==3 and tags=='2':
            bq={'00':ch[0],'01':ch[1],'1':ch[2]}
        else:
            bq={'00':ch[0],'01':ch[1],'10':ch[2],'11':ch[3]}
        d[z]=bq
    else:
        dt[z]=(chai[1:],kind[1:],length[1:],tags[1:],jg[1:],kb[1:])
f.close()
number=0
f=open('qc.txt',encoding='utf-8',mode='w')
for i in gb:
    z=i[0]
    y=i[1]
    if z in dt:
        b1,b2,b3,g1,g2,g3=dt[z][0],dt[z][1],dt[z][2],dt[z][3],dt[z][4],dt[z][5]
        if b2=='':
            f.write(z+'\t'+y[0]+'\t'+zg2.get(g1,b1[:2])+'\t'+b1[-1]+'\t'+b1[-1]+'\t'+b1[-1]+'\n')
        elif b3=='':
            f.write(z+'\t'+y[0]+'\t'+zg2.get(g1,b1[:2])+'\t'+zg3.get(g2,b2[:2])+'\t'+b2[-1]+'\t'+b2[-1]+'\n')
        else:
            f.write(z+'\t'+y[0]+'\t'+zg2.get(g1,b1[:2])+'\t'+zg3.get(g2,b2[:2])+'\t'+zg3.get(g3,b3[:2])+'\t'+b3[-1]+'\n')
    else:
        xm1=0
        x=z
        while x not in dt:
            x=d[x].get('0',d[x].get('00'))
            if x[0]!="<":
                x=x[0]
            if x in zg2:
                xm1=x
                break
        if xm1==0:
            xm1=zg2.get(dt[x][3],dt[x][0][:2])
        xm2=0
        x=d[z].get('1',d[z].get('10'))
        if x[0]!="<":
            x=x[0]
        while x not in dt:
            x=d[x].get('0',d[x].get('00'))
            if x[0]!="<":
                x=x[0]
            if x in zg3:
                xm2=x
                break
        if xm2==0:
            xm2=zg3.get(dt[x][3],dt[x][0][:2])
        xm3=0
        if '11' in d[z]:
            x=d[z]['11']
            if x[0]!="<":
                x=x[0]
            while x not in dt:
                x=d[x].get('0',d[x].get('00'))
                if x[0]!="<":
                    x=x[0]
                if x in zg3:
                    xm3=x
                    break
            if xm3==0:
                xm3=zg3.get(dt[x][3],dt[x][0][:2])
        else:
            x=d[z]['1']
            if x[0]!="<":
                x=x[0]
            if x in dt and dt[x][1]!='':
                xm3=zg3.get(dt[x][4],dt[x][1][:2])
            elif x in d:
                w=d[x].get('1',d[x].get('10'))
                if w[0]!="<":
                    w=w[0]
                while w not in dt:
                    w=d[w].get('0',d[w].get('00'))
                    if w[0]!="<":
                        w=w[0]
                    if w in zg3:
                        xm3=w
                        break
                if xm3==0:
                    xm3=zg3.get(dt[w][3],dt[w][0][:2])
            else:
                xm3=dt[x][0][-1]
        xm4=0
        x=z
        while x not in dt:
            x=d[x].get('1',d[x].get('11'))
            if x[0]!="<":
                x=x[0]
        xm4=(dt[x][0]+dt[x][1]+dt[x][2])[-1]
        f.write(z+'\t'+y[0]+'\t'+xm1+'\t'+xm2+'\t'+xm3+'\t'+xm4+'\n')
f.close()
