import subprocess
import sys
import os

def get_options(symbol, option=None, outdir=None, refresh_option=None):
    args = ["python", "get_options.py"] 

    if refresh_option:
        args.append(refresh_option) 

    if option:
        args.append(option)
    args.append(symbol)

    if outdir and not os.path.isdir(outdir):
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
    print("usage: python get_all.py [--reload|--useold|--dataonly] [stocklist_file] [out_dir]")
    sys.exit(0)

argnum = 1

refresh_option = None   # or "--reload" or "--useold" or "--dataonly"
if sys.argv[argnum] in ("--reload", "--useold", "--dataonly"):
    refresh_option = sys.argv[argnum]
    argnum += 1

stocklist_file = sys.argv[argnum]
argnum += 1
if not os.path.isfile(stocklist_file):
    print(f"{stocklist_file} not found")
    sys.exit(1)

folder = None
if len(sys.argv) > argnum:
    folder = sys.argv[argnum]
    print(f"argnum: {argnum} folder: {folder}")

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
        
        # do ic (or just update data files in case of reload=--dataonly)
        outdir = None
        if folder:
            outdir = folder + "/ic"
        rc = get_options(symbol, outdir=outdir, refresh_option=refresh_option)
        if rc == 0:
            symbols.append(symbol)    
        
        if refresh_option != "--dataonly":
            # do puts
            if folder:
                outdir = folder + "/puts"
            rc = get_options(symbol, option="--puts", outdir=outdir, refresh_option=refresh_option) 
            #print(f"{cnt}: {len(fields)}")
        
            # do calls
            if folder:
                outdir = folder + "/calls"
            rc = get_options(symbol, option="--calls", outdir=outdir, refresh_option=refresh_option)
        
        line = f.readline()
        

print(f"got data for {len(symbols)} symbols")
