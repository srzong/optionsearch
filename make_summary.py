import os
import sys
import time
from datetime import datetime

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

#
# Main
#
if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
    print("Usage: python get_summary.py [stocklist_file] [outdir]")
    sys.exit(1)

stocklist_file = "stocks.csv"
outdir = "out"

if len(sys.argv) > 1:
    stocklist_file = sys.argv[1]

if len(sys.argv) > 2:
    outdir = sys.argv[2]

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
            #print(f"ignoring symbol: {symbol}")
            line = f.readline()
            continue
        #print(symbol)
        symbols.append(symbol)
        line = f.readline()

if len(symbols) == 0:
    eprint("no symbols found!")
    sys.exit(1)

icdir = f"{outdir}/ic/"
calldir = f"{outdir}/calls/"
putdir = f"{outdir}/puts/"

dt = datetime.fromtimestamp(time.time())
print(f"{dt.month}/{dt.day}/{dt.year}")
print(",,IC,,,,,CALL,,,,,PUT,,,,")
print("SYMBOL,UNDERLYING,NUM,MAX ET,TC,TC/W,BEVEN,NUM,MAX ETC,TCC,TCC/W,BEVENC,NUM,MAX ETP,TPC,TPC/W,BEVENP")
for symbol in symbols:
    #print(f"got symbol: {symbol}")
    underlying = None
    counts = {"et": 0, "etc": 0, "etp": 0}
    variables = ("et", "etc", "etp", "tc", "tc_width", "tcc", "tcc_w", "tpc", "tpc_w", "beven", "bevenc","bevenp")
    
    filename = symbol + ".txt"
    filepaths = (icdir + filename, calldir+filename, putdir+filename)
    values = {}
    for filepath in filepaths:
        #print(f"reading: {filepath}, symbol: [{symbol}]" )
        if not os.path.isfile(filepath):
            eprint(f"file: {filepath} not found")
            continue
        got_max_et = False  
        get_values = False
        with open(filepath, "r") as f:
            while True:
                line = f.readline()
                if not line:
                    break
                line = line.strip()
                fields = line.split()
                if len(fields) == 0:
                    continue
                if not underlying and line.find("underlying") > -1:
                    underlying = float(fields[-1])
                for variable in variables:
                    if line.startswith(variable+':'):
                        value = float(fields[1])
                        if variable.startswith("et"):
                            counts[variable] = counts[variable] + 1
                            # handler for et, etc, etp
                            if variable not in values or value > values[variable]:
                                values[variable] = value
                                get_values = True
                            else:
                                # not max et/etc/etp
                                get_values = False
                        elif get_values:
                            values[variable] = value
                        else:
                            pass  # ignore
       
    if counts["et"] > 0 and "et" in values and values["et"] > 0.0:
        for variable in variables:
            if variable not in values:
                eprint(f"{variable} not found")
                values[variable] = 0.0
         
        print(f"{symbol},${underlying},{counts['et']},{values['et']:.3f},{values['tc']:.3f},{values['tcc_w']:.3f},{values['beven']:.3f},{counts['etc']},{values['etc']:.3f},{values['tcc']:.3f},{values['tcc_w']:.3f},{values['bevenc']:.3f},{counts['etp']},{values['etp']:.3f},{values['tpc']:.3f},{values['tpc_w']:.3f},{values['bevenp']:.3f}")
 


