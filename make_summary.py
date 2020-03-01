import os
import sys
import time
from datetime import datetime

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def print_usage():
    print("Usage: python make_summary.py [stocklist_file] [outdir]")


#
# Main
#
if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
    print_usage()
    sys.exit(1)

if len(sys.argv) <= 2 or sys.argv[1] in ('-h', '--help'):
    print_usage()
    sys.exit(0)

stocklist_file = sys.argv[1]
if not os.path.isfile(stocklist_file):
    eprint(f"{stocklist_file} not found")
    sys.exit(1)
 
outdir = sys.argv[2]
if not os.path.isdir(outdir):
    eprint(f"{outdir} not found")
    sys.exit(1)

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
print(",,IC,,,,,,,CALL,,,,,,,PUT,,,,,,,")
print("SYMBOL,UNDERLYING,NUM,MAX ET,TC,TC/W,TC/U,BEVEN,IC,NUM,MAX ETC,TCC,TCC/W,TCC/U,BEVENC,CSpd,NUM,MAX ETP,TPC,TPC/W,TPC/U,BEVENP,PSpd")
for symbol in symbols:
    #print(f"got symbol: {symbol}")
    underlying = 0.0
    volatility = 0.0
    interestRate = 0.0
    ic = None
    counts = {"et": 0, "etc": 0, "etp": 0}
    variables = ("et", "etc", "etp", "tc", "tc_w", "tc_u", "tcc", "tcc_w", "tcc_u", "tpc", "tpc_w", "tpc_u", "beven", "bevenc","bevenp", "IC", "CSpd", "PSpd")
    
    filename = symbol + ".txt"
    filepaths = (icdir + filename, calldir+filename, putdir+filename)
    values = {}
    for filepath in filepaths:
        #eprint(f"reading: {filepath}, symbol: [{symbol}]" )
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
                #eprint("line:", line)
                fields = line.split()
                if len(fields) == 0:
                    continue
                if not underlying and line.find("underlying:") > -1:
                    underlying = float(fields[2])
                if not volatility and line.find("volatility:") > -1:
                    volatility = float(fields[2])
                if not interestRate and line.find("interestRate:") > -1:
                    interestRate = float(fields[2])
            
                for variable in variables:
                    if line.startswith(variable+':'):
                        try:
                            value = float(fields[1])
                        except ValueError:
                            value = fields[1]   # string value
                            #eprint(f"ValueError, got: [{value}]")
                        if variable in ("IC", "CSpd", "PSpd"):
                            ic = fields[1]
                            #eprint(f"setting IC {variable} to {ic} ")
                        elif variable.startswith("et"):
                            counts[variable] = counts[variable] + 1
                            # handler for et, etc, etp
                            if variable not in values or value > values[variable]:
                                values[variable] = value
                                get_values = True
                                # copy in the IC (which we should have already scanned)
                                if variable == "et":
                                    #eprint(f"setting values IC with {ic}")
                                    values["IC"] = ic
                                elif variable == "etc":
                                    #eprint(f"setting values CSpd with {ic}")
                                    values["CSpd"] = ic
                                elif variable == "etp":
                                    #eprint(f"setting values PSpd with {ic}")
                                    values["PSpd"] = ic
                                else:
                                    #eprint("expected to have ic value")
                                    pass
                            else:
                                # not max et/etc/etp
                                get_values = False
                        elif get_values:
                            values[variable] = value
                        else:
                            pass  # ignore
       
    # if counts["et"] > 0 and "et" in values and values["et"] > 0.0:
    if True:
        for variable in variables:
            if variable not in values:
                eprint(f"{symbol}: {variable} not found")
                values[variable] = 0.0
        print(f"{symbol},${underlying},{counts['et']},{values['et']:.3f},{values['tc']:.3f},{values['tc_w']:.3f},{values['tc_u']:.3f},{values['beven']:.3f},{values['IC']},{counts['etc']},{values['etc']:.3f},{values['tcc']:.3f},{values['tcc_w']:.3f},{values['tcc_u']:.3f},{values['bevenc']:.3f},{values['CSpd']},{counts['etp']},{values['etp']:.3f},{values['tpc']:.3f},{values['tpc_w']:.3f},{values['tpc_u']:.3f},{values['bevenp']:.3f},{values['PSpd']}")
 


