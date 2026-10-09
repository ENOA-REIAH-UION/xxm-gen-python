d={}
szm={'a':'r','e':'r','o':'r','z':'i'}
f=open('dp.txt',encoding='utf-8',mode='r')
for line in f:
    z,y,p=line.strip('\r\n').split('\t')
    if z not in d:
        d[z]=[[szm.get(y[0],y[0]),int(p)]]
    else:
        q=0
        for i in d[z]:
            if szm.get(y[0],y[0]) == i[0]:
                i[1]+=int(p)
                q=1
        if q==0:
            d[z].append([szm.get(y[0],y[0]),int(p)])
f.close()
f=open('info.txt',encoding='utf-8',mode='r')
fw=open('info_new.txt',encoding='utf-8',mode='w')
zi=[]
result=[]
for line in f:
    z,s,c1,c2,c3,c4,p,o=line.strip('\r\n').split('\t')
    if z not in zi:
        zi.append(z)
        for i in d[z]:
            try:
                result.append([z,i[0],c1,c2,c3,c4,int(int(p)*i[1]/sum((x[1] for x in d[z])))])
            except ZeroDivisionError:
                result.append([z,i[0],c1,c2,c3,c4,0])
result.sort(key=lambda x:x[6],reverse=True)
for i in result:
    fw.write('\t'.join(map(str,i))+'\n')
f.close()
fw.close()
