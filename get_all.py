import subprocess
import sys
import os

def get_options(symbol, option=None, outdir=None, reload=False):
    args = ["python", "get_options.py"] 

    if reload:
        args.append("--reload") 

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
if len(sys.argv) <= 2 or sys.argv[1] in ('-h', '--help'):
    print("usage: python get_all.py [--reload] [stocklist_file] [out_dir]")
    sys.exit(0)

argnum = 1
reload = False
if sys.argv[argnum] == "--reload":
    reload = True
    argnum += 1
stocklist_file = sys.argv[argnum]
argnum += 1
if not os.path.isfile(stocklist_file):
    print(f"{stocklist_file} not found")
    sys.exit(1)

folder = sys.argv[argnum]

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
        """
        # do ic
        outdir = folder + "/ic"
        rc = get_options(symbol, outdir=outdir, reload=reload)
        if rc == 0:
            symbols.append(symbol)    
        """
        # do puts
        outdir = folder + "/puts"
        rc = get_options(symbol, option="--puts", outdir=outdir, reload=reload) 
        #print(f"{cnt}: {len(fields)}")
        
        # do calls
        outdir = folder + "/calls"
        rc = get_options(symbol, option="--calls", outdir=outdir, reload=reload)
        
        line = f.readline()
        

print(f"got data for {len(symbols)} symbols")
