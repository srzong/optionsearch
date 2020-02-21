import subprocess
import sys
import os

def get_options(symbol, option=None, outdir=None):
    args = ["python", "get_options.py"]  #, "--reload"]
    if option:
        args.append(option)
    args.append(symbol)

    if not outdir:
        outdir = "out"
    if not os.path.isdir(outdir):
        os.mkdir(outdir)
    
    fout = open("tmp.txt", "w")
    result = subprocess.run(args, stdout=fout)
    fout.close()
    if result.returncode != 0:
        print(f"got rc: {result.returncode} for symbol: {symbol}")
    elif outdir: 
        os.rename("tmp.txt", f"{outdir}/{symbol}.txt")
    return result.returncode

#
# main
#
if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help'):
    print("usage: python get_all.py [stocklist_file] [out_dir]")
    sys.exit(0)

stocklist_file = "stocks.csv"
folder = "out"
if len(sys.argv) > 1:
    stocklist_file = sys.argv[1]

if len(sys.argv) > 2:
    folder = sys.argv[2]

if not os.path.isdir(folder):
    os.mkdir(folder)

symbols = []
with open(stocklist_file, "r") as f:
    line = f.readline()
    while line:
        fields = line.strip().split(',')
        if not fields:
            line = f.readline()
            continue
        symbol = fields[0]
        if not symbol.isupper():
            print(f"ignoring symbol: {symbol}")
            line = f.readline()
            continue
        print(symbol)

        # do ic
        outdir = folder + "/ic"
        rc = get_options(symbol, outdir=outdir)
        if rc == 0:
            symbols.append(symbol)    
        
        # do puts
        outdir = folder + "/puts"
        rc = get_options(symbol, option="--puts", outdir=outdir) 
        #print(f"{cnt}: {len(fields)}")
        
        outdir = folder + "/calls"
        rc = get_options(symbol, option="--calls", outdir=outdir)
        line = f.readline()


print(f"got data for {len(symbols)} symbols")
cnt = 0
for symbol in symbols:
    rc = get_options(symbol, outdir="out")
    if rc == 0:
        cnt += 1
print(f"got candidates for {cnt} symbols")
