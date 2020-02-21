import os
import sys
import time
from datetime import datetime

outdir = "out"
if len(sys.argv) > 1:
    outdir = sys.argv[1]
outfiles = os.listdir(outdir)
dt = datetime.fromtimestamp(time.time())
print(f"{dt.month}/{dt.day}/{dt.year}")
print(",,IC,,,,CALL,,,,PUT,,,,")
print("SYMBOL,UNDERLYING,NUM,MAX ET,TC,TC/W,NUM,MAX ETC,TCC,TCC/W,NUM,MAX ETP,TPC,TPC/W,BEVEN")
for filename in outfiles:
    if not filename.endswith(".txt"):
        continue
    filepath = outdir + "/" + filename
    symbol = filename[:-4]
    #print(f"reading: {filepath}, symbol: [{symbol}]" )
    underlying = None
    out_num = 0
    out_max_et = None
    out_tc = None
    out_tcw = None
    get_next_tc = False
    get_next_tcw = False
    get_beven = False
    call_num = 0
    call_max_etc = -999.0
    call_tcc = -999.0
    call_tccw = -999.0
    put_num = 0
    put_max_etp = -999.0
    put_tpc = -999.0
    put_tpcw = -999.0 
    beven = 0.0

    

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
            if line.startswith("et:"):
                out_num += 1
                et  = float(fields[1])    
                if not out_max_et or et > out_max_et:
                    out_max_et = et
                    get_next_tc = True
                    get_next_tcw = True
                    get_beven = True
            if get_next_tc and line.startswith("tc:"):
                out_tc = float(fields[1])
                get_next_tc = False
            if get_next_tcw and line.startswith("tc_width"):
                out_tcw = float(fields[1])
                get_next_tcw = False
            if get_beven and line.startswith("beven:"):
                beven = float(fields[1])
                get_beven = False
    filepath = outdir + f"calls/{symbol}.txt"
    get_next_tc = False
    get_next_tcw = False
    get_beven = False
    with open(filepath, "r") as f:
        while True:
            line = f.readline()
            if not line:
                break
            line = line.strip()
            fields = line.split()
            if len(fields) == 0:
                continue
            if line.startswith("etc:"):
                et = float(fields[1])    
                if et > 0.0:
                    call_num += 1
                if not call_max_etc or et > call_max_etc:
                    call_max_etc = et
                    get_next_tc = True
                    get_next_tcw = True
                    get_beven = True
            if get_next_tc and line.startswith("tcc:"):
                call_tcc = float(fields[1])
                get_next_tc = False
            if get_next_tcw and line.startswith("tcc_w:"):
                call_tccw = float(fields[1])
                get_next_tcw = False
            if get_beven and line.startswith("beven:"):
                beven = float(fields[1])
                get_beven = False
    filepath = outdir + f"puts/{symbol}.txt"
    get_next_tc = False
    get_next_tcw = False
    get_beven = False
    with open(filepath, "r") as f:
        while True:
            line = f.readline()
            if not line:
                break
            line = line.strip()
            fields = line.split()
            if len(fields) == 0:
                continue
            if line.startswith("etp:"):
                
                et = float(fields[1])  
                if et > 0.0:
                    put_num += 1  
                if not put_max_etp or et > put_max_etp:
                    put_max_etp = et
                    get_next_tc = True
                    get_next_tcw = True
            if get_next_tc and line.startswith("tpc:"):
                put_tpc = float(fields[1])
                get_next_tc = False
            if get_next_tcw and line.startswith("tpc_w:"):
                put_tpcw = float(fields[1])
                get_next_tcw = False
    
       
    if out_num and out_max_et and out_max_et > 0.0 and out_tc and out_tcw:
        print(f"{symbol},${underlying},{out_num},{out_max_et:.3f},{out_tc:.3f},{out_tcw:.3f},{call_num},{call_max_etc:.3f},{call_tcc:.3f},{call_tccw:.3f},{put_num},{put_max_etp:.3f},{put_tpc:.3f},{put_tpcw:.3f},{beven:.3f}")
 


