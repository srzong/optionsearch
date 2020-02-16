import subprocess
import os

def get_options(symbol, option=None, outdir=None):
    args = ["python", "get_options.py"]
    if option:
        args.append(option)
    args.append(symbol)
    
    fout = open("tmp.txt", "w")
    result = subprocess.run(args, stdout=fout)
    fout.close()
    if result.returncode != 0:
        print(f"got rc: {result.returncode} for symbol: {symbol}")
    elif outdir: 
        os.rename("tmp.txt", f"{outdir}/{symbol}.txt")
    return result.returncode

symbols = []
with open("stock8000.csv", "r") as f:
    line = f.readline()
    while line:
        fields = line.strip().split(',')
        if len(fields) == 9:
            symbol = fields[0]
            if not symbol.isupper():
                print(f"ignoring symbol: {symbol}")
                line = f.readline()
                continue
            print(symbol)
            rc = get_options(symbol, option="--calls", outdir="calls")
            if rc == 0:
                symbols.append(symbol)     
            rc = get_options(symbol, option="--puts", outdir="puts") 
        #print(f"{cnt}: {len(fields)}")
        line = f.readline()

print(f"got data for {len(symbols)} symbols")
cnt = 0
for symbol in symbols:
    rc = get_options(symbol, outdir="out")
    if rc == 0:
        cnt += 1
print(f"got candidates for {cnt} symbols")
