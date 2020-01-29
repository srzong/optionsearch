import sys
import time
from datetime import datetime
import requests

ARGS = {}

CS_DELTA_RANGE = (0.165,0.4)
CB_DELTA_RANGE = (0.05,0.16)
PS_DELTA_RANGE = (-0.4,-0.165)
PB_DELTA_RANGE = (-0.16,-0.05)
SELL_SYMMETRY = 0.04
BUY_SYMMETRY = 0.05
ET_WIDTH_BOUND = 0
TC_WIDTH_BOUND = 0.334
CHECK_ALL = False
CHECK_ET = False
CHECK_TC = False


def check_delta_bound(delta, option_type=None):
    if option_type == "cs":
        delta_range = CS_DELTA_RANGE
    elif option_type == "cb":
        delta_range = CB_DELTA_RANGE
    elif option_type == "ps":
        delta_range = PS_DELTA_RANGE
    elif option_type == "pb":
        delta_range = PB_DELTA_RANGE
    else:
        print("invalid call type")
        sys.exit(1)
    if ARGS["skip_delta"]:
        return True
    
    if delta >= delta_range[0] and delta <= delta_range[1]:
        return True

    return False

def option_str(option):
    desc = option["description"]
    delta = option["delta"]
    strike = option["strike"]
    price = option["price"]

    s = f"{desc} -- delta: {delta:.2f} strike: {strike:.2f} price: {price:.2f} "
    return s

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def get_headers():
    with open("auth_token", "r") as f:
        data = f.read().strip()
    headers = {"Authorization": "Bearer " + data}
    return headers

class Candidate:
    def __init__(self, cs=None, cb=None, ps=None, pb=None, underlying=None):
        self._cs = cs
        self._cb = cb
        self._ps = ps
        self._pb = pb
        self._underlying = underlying
        self._tc_rank = None
        self._et_rank = None
        self._et_width_rank = None
        self._et_tc_rank = None
        self._tc_width_rank = None

        css = cs["strike"]
        cbs = cb["strike"]
        pss = ps["strike"]
        pbs = pb["strike"]
        csp = cs["price"]
        cbp = cb["price"]
        psp = ps["price"]
        pbp = pb["price"]
        csd = cs["delta"]
        cbd = cb["delta"]
        psd = ps["delta"]
        pbd = pb["delta"] 

        print("******************")
        print("css:", css)
        print("cbs:", cbs)
        print("pss:", pss)
        print("pbs:", pbs) 
        print("price")
        print("csp:", csp)
        print("cbp:", cbp)
        print("psp:", psp)   
        print("pbp:", pbp) 
        print("strike")
        print("csd:", csd)
        print("cbd:", cbd)
        print("psd:", psd)
        print("pbd:", pbd)   
        print("******************")
        
        tc = csp - cbp + psp - pbp
        width = ((cbs - css) + (pss - pbs)) * 0.5

        print("tc:", tc)
        print("width:", width)
        print("cbs - css:", (cbs - css))
        print("pss - pbs:", pss - pbs)
      
        try:
            tc_width = tc / width
            etc = tc * (1.0 - csd + psd) 
            delta_cc = tc * (csd - cbd)/(cbs - css)
            delta_pc = tc * (psd - pbd)/(pss - pbs) 
            delta_cd = csd - cbd - delta_cc
            delta_pd = psd - pbd - delta_pc 
            cd = cbs - css - tc
            pd = pss - pbs - tc
            print("d_cc:", delta_cc)
            print("d_pc:", delta_pc)   
            print("d_cd:", delta_cd)
            print("d_pd:", delta_pd)            
            print("cd:", cd)            
            print("pd:", pd)

            ecch = 0.5 * tc * delta_cc
            epch = -0.5 * tc * delta_pc
            ecdh = -0.5 * cd * delta_cd 
            epdh = 0.5 * pd * delta_pd 
            ecd = -cd * cbd 
            epd = pd * pbd 
            et = etc + ecch + ecdh + epch + epdh + ecd + epd

            print("etc:", etc)
            print("ecch:", ecch)
            print("epch:", epch)
            print("ecdh:", ecdh)
            print("epdh:", epdh)
            print("ecd:", ecd)
            print("epd:", epd)
            print("et:", et)

            et_width = et/width
            et_tc = et/tc

            if cd > pd:
                ml = cd
            else:
                ml = pd

            et_ml = et/ml
            tc_ml = tc/ml
            et_tc = et/tc

            print("ml:", ml)
            print("tc/ml:", tc_ml)
            print("et/ml:", et_ml)
            print("tc/width:", tc_width)
            print("et/width:", et_width)
            print("et/tc:", et_tc)

            # properties
            self._tc = tc
            self._width = width
            self._et = et
            self._tc_width = tc_width
            self._et_width = et_width
            self._et_tc = et_tc
            self._ml = ml
            self._et_ml = et_ml
            self._tc_ml = tc_ml
        except ZeroDivisionError as e:
            #print("zerodivisionerror")
            #raise e
            #sys.exit(1)
            self._tc = None
            self._width = None
            self._et = None
            self._tc_width = None
            self._et_width = None
            self._et_tc = None
            self._ml = None
            self._et_ml = None
            self._tc_ml= None


    
    def __str__(self):
        cs_str = option_str(self._cs)
        cb_str = option_str(self._cb)
        pb_str = option_str(self._pb)
        ps_str = option_str(self._ps)
        return f"{cs_str}/{cb_str}/{pb_str}/{ps_str}"

    def print_verbose(self):
        #print(candidate.keys())
        print() 

        print("cs:",option_str(self._cs))
        print("cb:", option_str(self._cb))
        print("ps:", option_str(self._ps))
        print("pb:", option_str(self._pb))
        print("----")
        
        if self._et:
            print(f"et: {self._et:.3f} rank: {self._et_rank}")
            print(f"tc: {self._tc:.2f} rank: {self._tc_rank}")
            print(f"width: {self._width:.2f}")
            print(f"ml: {self._ml:.2f}")
            print(f"tc/width: {100*self._tc_width:.2f}% rank: {self._tc_width_rank}")
            #print(f"tc/ml: {tc_ml:.2f} rank: {tc_ml_rank}")
            print(f"et/width: {100*self._et_width:.2f}% rank: {self._et_width_rank}")
            #print(f"et/ml: {Et_ml:.2f} rank: {Et_ml_rank}")
            print(f"et/tc: {100*self._et_tc:.2f}% rank: {self._et_tc_rank}")
    
    @property
    def cs(self):
        return self._cs

    @property
    def cb(self):
        return self._cb

    @property
    def pb(self):
        return self._pb

    @property
    def ps(self):
        return self._ps

    @property
    def underlying(self):
        return self._underlying

    @property
    def tc(self):
        return 
    @property
    def width(self):
        return self._width

    @property
    def et(self):
        return self._et
    
    @property
    def tc_width(self):
        return self._tc_width

    @property
    def et_width(self):
        return self._et_width

    @property
    def et_tc(self):
        return self._et_tc

    @property
    def ml(self):
        return self._ml
    
    @property
    def et_ml(self):
        return self._et_ml

    @property
    def tc_ml(self):
        return self._tc_ml

    @property
    def tc_rank(self):
        return self._tc_rank

    @property
    def et_width_rank(self):
        return self._et_width_rank

    @property
    def et_tc_rank(self):
        return self._et_tc_rank

    def set_tc_rank(self, rank):
        self._tc_rank = rank

    def set_et_width_rank(self, rank):
        self._et_width_rank = rank

    def set_et_tc_rank(self, rank):
        self._et_tc_rank = rank

    def meets_requirements(self):
        if self._cs["strike"] >= self.cb["strike"]:
            print("bad call strike: sell>buy")
            return False
        if self._pb["strike"] >= self._ps["strike"]:
            print("bad put strike: buy>sell")
            return False
    
        if self._ps["strike"] >= self._cs["strike"]:
            print("bad call/put strikes")
            return False

        if not self._ps["price"] >= self._pb["price"]:
            print('bad price: put sell < buy')
            return False
        if not self._cs["price"] >= self._cb["price"]:
            print("bad price: call sell < buy")
            return False
                     
        if not ARGS["skip_delta"]:
            if not check_delta_bound(self._cs["delta"], option_type="cs"):
                print("bad bound: call sell delta")
                return False
            if not check_delta_bound(self._cb["delta"], option_type="cb"):
                print("bad bound: call buy delta")
                return False
            if not check_delta_bound(self._ps["delta"], option_type="ps"):
                print("bad bound: put sell delta")
                return False
            if not check_delta_bound(self._pb["delta"], option_type="pb"):
                print("bad bound: put buy delta")
                return False
    
        symms = self._cs["delta"] + self._ps["delta"]
        print("symms = ", symms)
        if -SELL_SYMMETRY >= symms or symms >= SELL_SYMMETRY:
            print("bad symmetry: sell")
            return False

        if self._ps["strike"] - self._pb["strike"] <= self._tc:
            print("bad tail: put")
            return False   

        if self._cb["strike"] - self._cs["strike"] <= self._tc:
            print("bad tail: call")
            return False  

        if self.et_width <= ET_WIDTH_BOUND:
            if CHECK_ALL  or CHECK_ET:
                print("bad et/width check")
                return False
        if self.tc_width <= TC_WIDTH_BOUND:
            if CHECK_ALL  or CHECK_TC:
                print("bad tc/width check")
                return False

        #if self._et is None or self._et <= -.1:
        if self._et <= 0.01:
            print("bad et")
            return False
    
        return True

        
 

def printCandidates(candidates):
    for candidate in candidates:
        candidate.print_verbose()
        print("------------")

def get_chains(symbol):
    seconds_in_day = 24.0 * 60.0 * 60.0
    exp_target_min = time.time() + 41.0 * seconds_in_day
    dt_min = datetime.fromtimestamp(exp_target_min)
    exp_target_max = time.time() + 60.0 * seconds_in_day
    dt_max = datetime.fromtimestamp(exp_target_max)
    

    headers = get_headers()
    params = {}
    params["symbol"] = symbol
    params["strikeCount"] = 200
    params["includeQuotes"] = True
    params["strategy"] = "ANALYTICAL"
    params["interval"] = 1
    params["fromDate"] = f"{dt_min.year}-{dt_min.month}-{dt_min.day}"
    params["toDate"] = f"{dt_max.year}-{dt_max.month}-{dt_max.day}"
    print(f"fromDate: {dt_min.year}-{dt_min.month}-{dt_min.day}")
    print(f"toDate: {dt_max.year}-{dt_max.month}-{dt_max.day}")
    params["daysToExpiration"] = 45
    req = "https://api.tdameritrade.com/v1/marketdata/chains"
    rsp = requests.get(req, params=params, headers=headers)
    if rsp.status_code != 200:
        print("got bad status code:", rsp.status_code)
        return None
    rsp_json = rsp.json()
    if rsp_json["status"] == "FAILED":
        print("got FAILED status")
        return None
    #print(rsp_json)
    return rsp_json

def get_options(option_map, underlying):
    results = []
    expire_date = None
    for expDate in option_map:
        if expire_date:
            if expDate != expire_date:
                continue
        else:
            expire_date = expDate
        bundle = option_map[expDate]
        for strikePrice in bundle:
            options = bundle[strikePrice]
            for option in options:
                description = option["description"]
                print("description:", description)
                delta = option["delta"]
                strike = float(strikePrice)
                if description.endswith("Put"):
                    if underlying <= strike:
                        print(f"skip put, underlying: {underlying} strike: {strike}")
                        continue
                elif description.endswith("Call"):
                    if underlying >= strike:
                        print(f"skip call, underlying: {underlying} strike: {strike}")
                        continue
                else:
                    print(f"unexpected description: {description}")
                    sys.exit(1)
                price = (option["bid"] + option["ask"])/2.0
                item = {"description": description, "delta": delta, "strike": strike, "price": price}
                """
                if  delta >= PSS_RANGE[0] and delta <= PSS_RANGE[1]:
                    pss_options.append(item)
                elif delta >= PBS_RANGE[0] and delta <= PBS_RANGE[1]:
                    pbs_options.append(item)
                else:
                    print(f"skip put option: {description} delta: {delta}")
                """
                results.append(item)
    return results
    

def get_contracts(chains):
    underlying = chains["underlyingPrice"]
    putMap = chains["putExpDateMap"]
    callMap = chains["callExpDateMap"]
    
    put_options = get_options(putMap, underlying)
    print(f"got {len(put_options)} put options")
    call_options = get_options(callMap, underlying)
    print(f"got {len(call_options)} call options")

    return {"underlying": underlying, "call": call_options, "put": put_options}   

def get_candidates(contracts):
    candidates = []
    call_list = contracts["call"]
    put_list = contracts["put"]
    underlying = contracts["underlying"]
    total_count = 0
    meet_requirements_count = 0
    
    for i in range(len(call_list) - 1):
        cs = call_list[i]
        last_strike = cs["strike"]
        for j in range(i+1, len(call_list)):
            cb = call_list[j]
            this_strike = cb["strike"]
            
            if this_strike <= last_strike:
                print(f"unexpected call last_strike: {last_strike} this_strike: {this_strike}")
                sys.exit(1)
            for k in range(len(put_list) - 1):
                pb = put_list[k]
                last_strike = pb["strike"]
                for l in range(k+1, len(put_list)):
                    ps = put_list[l]
                    this_strike = ps["strike"]
                    if this_strike <= last_strike:
                        print(f"unexpected put last_strike: {last_strike} this_strike: {this_strike}")
                        sys.exit(1)

                    candidate = Candidate(cs=cs, cb=cb, pb=pb, ps=ps, underlying=underlying)
                    total_count += 1

                    if  candidate.meets_requirements():
                        candidates.append(candidate)
                        meet_requirements_count += 1

    print ("----------------------")
    print("total candidates:", total_count)
    print("meet req candidates:", meet_requirements_count)                    
    return candidates
        

def print_usage():
    print("usage: python get_options.py [--skip-delta] SYM")


#
# Main
#
if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
    print_usage()
    sys.exit(1)

symbols = []
ARGS["skip_delta"] = False
for argn in range(1, len(sys.argv)):
    print("got arg:", sys.argv[argn])
    argval = sys.argv[argn]
    if argval.startswith('-'):
        if argval == "--skip-delta":
            ARGS["skip_delta"] = True
        else:
            print_usage()
            sys.exit(1)
    else:
        symbols.append(argval)
if not symbols:
    print_usage()
    sys.exit(1)
symbol = symbols[0]
print("getting symbol:", symbol)
chains = get_chains(symbol)
if not chains:
    sys.exit(1)
contracts = get_contracts(chains)

for k in ("call", "put"):
    options = contracts[k]
    print(k, len(options))
    for option in options:
        print(option["description"], option["delta"])

for k in ("call", "put"):
    options = contracts[k]
    if len(options) == 0:
        print("no candidates!")
        sys.exit(0)

candidates = get_candidates(contracts)
print("got", len(candidates), "candidates")
print("======================")

"""
for key in ("Tc_ml", "Et", "Et_ml", "Tc_width", "Et_width", "Et_tc", "Tc"):
    candidates.sort(key = lambda candidate: candidate[key], reverse=True)
    rank = 1
    for candidate in candidates:
        candidate[key + "_rank"] = rank
        rank += 1


print("======================")

candidates.sort(key = lambda candidate: candidate["Et"], reverse=True)
rank = 1
for candidate in candidates:
    candidate["EtRank"] = rank
    rank += 1
"""
printCandidates(candidates)

 

