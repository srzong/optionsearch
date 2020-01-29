import sys
import time
import logging
from datetime import datetime
import requests

ARGS = {}

CS_DELTA_RANGE = (0.165,0.4)
CB_DELTA_RANGE = (0.05,0.16)
PS_DELTA_RANGE = (-0.4,-0.165)
PB_DELTA_RANGE = (-0.16,-0.05)
SELL_SYMMETRY = 0.03
BUY_SYMMETRY = 0.05
ET_WIDTH_BOUND = 0
TC_WIDTH_BOUND = 0.334
CHECK_ALL = False
CHECK_ET = False
CHECK_TC = False
loglevel = logging.ERROR  # DEBUG or INFO or ERROR


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
        logging.error("invalid call type")
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
        self.__ml_rank = None

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

        logging.info("******************")
        logging.info("strike")
        logging.info(f"css: {css:.3f}")
        logging.info(f"cbs: {cbs:.3f}")
        logging.info(f"pss: {pss:.3f}")
        logging.info(f"pbs: {pbs:.3f}") 
        logging.info("price")
        logging.info(f"csp: {csp:.3f}")
        logging.info(f"cbp: {cbp:.3f}")
        logging.info(f"psp: {psp:.3f}")   
        logging.info(f"pbp: {pbp:.3f}") 
        logging.info(f"delta")
        logging.info(f"csd: {csd:.3f}")
        logging.info(f"cbd: {cbd:.3f}")
        logging.info(f"psd: {psd:.3f}")
        logging.info(f"pbd: {pbd:.3f}")   
        logging.info("******************")
        
        tc = csp - cbp + psp - pbp
        width = ((cbs - css) + (pss - pbs)) * 0.5

        logging.info(f"tc: {tc:.3f}")
        logging.info(f"width: {width:.3f}")
        logging.info(f"cbs - css: {(cbs - css):.3f}")
        logging.info(f"pss - pbs: {(pss - pbs):.3f}")
      
        try:
            tc_width = tc / width
            etc = tc * (1.0 - csd + psd) 
            delta_cc = tc * (csd - cbd)/(cbs - css)
            delta_pc = tc * (psd - pbd)/(pss - pbs) 
            delta_cd = csd - cbd - delta_cc
            delta_pd = psd - pbd - delta_pc 
            cd = cbs - css - tc
            pd = pss - pbs - tc
            logging.info(f"d_cc: {delta_cc:.3f}")
            logging.info(f"d_pc:  {delta_pc:.3f}")   
            logging.info(f"d_cd: {delta_cd:.3f}")
            logging.info(f"d_pd: {delta_pd:.3f}")            
            logging.info(f"cd:  {cd:.3f}")            
            logging.info(f"pd: {pd:.3f}")

            ecch = 0.5 * tc * delta_cc
            epch = -0.5 * tc * delta_pc
            ecdh = -0.5 * cd * delta_cd 
            epdh = 0.5 * pd * delta_pd 
            ecd = -cd * cbd 
            epd = pd * pbd 
            et = etc + ecch + ecdh + epch + epdh + ecd + epd

            logging.info(f"etc: {etc:.3f}")
            logging.info(f"ecch: {ecch:.3f}")
            logging.info(f"epch: {epch:.3f}")
            logging.info(f"ecdh: {ecdh:.3f}")
            logging.info(f"epdh: {epdh:.3f}")
            logging.info(f"ecd: {ecd:.3f}")
            logging.info(f"epd: {epd:.3f}")
            logging.info(f"et: {et:.3f}")

            et_width = et/width
            et_tc = et/tc

            if cd > pd:
                ml = cd
            else:
                ml = pd

            et_ml = et/ml
            tc_ml = tc/ml
            et_tc = et/tc

            logging.info(f"ml: {ml:.3f}")
            logging.info(f"tc/ml: {tc_ml:.3f}")
            logging.info(f"et/ml: {et_ml:.3f}")
            logging.info(f"tc/width: {tc_width:.3f}")
            logging.info(f"et/width: {et_width:.3f}")
            logging.info(f"et/tc: {et_tc:.3f}")

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
        except ZeroDivisionError:
            logging.info("zerodivisionerror")
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
            for propname in {"et", "tc", "width", "ml", "tc_width", "et_width", "et_tc"}:
                propval = self.get_prop(propname)
                proprank = self.get_rank(propname)

                s = f"{propname}: {propval:.3f}"
                if proprank:
                    s += f" rank: {proprank}"
                if "sort_key" in ARGS and ARGS["sort_key"] == propname:
                    s += " *"
                print(s)
    
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

    def get_prop(self, propname):
        if propname == "tc_ml":
            return self._tc_ml
        if propname == "et":
            return self._et
        if propname == "et_ml":
            return self._et_ml
        if propname == "tc_width":
            return self._tc_width
        if propname == "et_width":
            return self._et_width
        if propname == "et_tc":
            return self._et_tc
        if propname == "tc":
            return self._tc
        if propname == "width":
            return self._width
        if propname == "ml":
            return self._ml
        logging.error(f"get_prop unexpected propname: [{propname}]")
        sys.exit(1)

    def set_prop(self, propname, value):
        if propname == "tc_ml":
            self._tc_ml = value
            return
        if propname == "et":
            self._et = value
            return
        if propname == "et_ml":
            self._et_ml = value
            return
        if propname == "tc_width":
            self._tc_width = value
            return
        if propname == "et_width":
            self._et_width = value
            return
        if propname == "et_tc":
            self._et_tc = value
            return
        if propname == "tc":
            self._tc = value
            return
        if propname == "width":
            self._width = value
            return
        if propname == "ml":
            self._ml = value
            return
        logging.error(f"set_prop unexpected propname: [{propname}]")
        sys.exit(1)

    def get_rank(self, propname):
        if propname == "tc_ml":
            return self._tc_ml_rank
        if propname == "et":
            return self._et_rank
        if propname == "et_ml":
            return self._et_ml_rank
        if propname == "tc_width":
            return self._tc_width_rank
        if propname == "et_width":
            return self._et_width_rank
        if propname == "et_tc":
            return self._et_tc_rank
        if propname == "tc":
            return self._tc_rank
        if propname == "width":
            return self._width_rank
        if propname == "ml":
            return self._ml_rank
        logging.error(f"get_rank unexpected propname: [{propname}]")
        sys.exit(1)

    def set_rank(self, propname, value):
        if propname == "tc_ml":
            self._tc_ml_rank = value
            return
        if propname == "et":
            self._et_rank = value
            return
        if propname == "et_ml":
            self._et_ml_rank = value
            return
        if propname == "tc_width":
            self._tc_width_rank = value
            return
        if propname == "et_width":
            self._et_width_rank = value
            return
        if propname == "et_tc":
            self._et_tc_rank = value
            return
        if propname == "tc":
            self._tc_rank = value
            return
        if propname == "width":
            self._width_rank = value
            return
        if propname == "ml":
            self._ml_rank = value
            return
        logging.error(f"set_rank unexpected propname: [{propname}]")
        sys.exit(1)
        

    def meets_requirements(self):
        if self._cs["strike"] >= self.cb["strike"]:
            logging.info("bad call strike: sell>buy")
            return False
        if self._pb["strike"] >= self._ps["strike"]:
            logging.info("bad put strike: buy>sell")
            return False
    
        if self._ps["strike"] >= self._cs["strike"]:
            logging.info("bad call/put strikes")
            return False

        if not self._ps["price"] >= self._pb["price"]:
            logging.info('bad price: put sell < buy')
            return False
        if not self._cs["price"] >= self._cb["price"]:
            logging.info("bad price: call sell < buy")
            return False
                     
        if not ARGS["skip_delta"]:
            if not check_delta_bound(self._cs["delta"], option_type="cs"):
                logging.info("bad bound: call sell delta")
                return False
            if not check_delta_bound(self._cb["delta"], option_type="cb"):
                logging.info("bad bound: call buy delta")
                return False
            if not check_delta_bound(self._ps["delta"], option_type="ps"):
                logging.info("bad bound: put sell delta")
                return False
            if not check_delta_bound(self._pb["delta"], option_type="pb"):
                logging.info("bad bound: put buy delta")
                return False
    
        symms = self._cs["delta"] + self._ps["delta"]
        logging.info("symms = ", symms)
        if -SELL_SYMMETRY >= symms or symms >= SELL_SYMMETRY:
            logging.info("bad symmetry: sell")
            return False

        if self._ps["strike"] - self._pb["strike"] <= self._tc:
            logging.info("bad tail: put")
            return False   

        if self._cb["strike"] - self._cs["strike"] <= self._tc:
            logging.info("bad tail: call")
            return False  

        if self.et_width <= ET_WIDTH_BOUND:
            if CHECK_ALL  or CHECK_ET:
                logging.info("bad et/width check")
                return False
        if self.tc_width <= TC_WIDTH_BOUND:
            if CHECK_ALL  or CHECK_TC:
                logging.info("bad tc/width check")
                return False

        #if self._et is None or self._et <= -.1:
        if self._et <= 0.01:
            logging.info("bad et")
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
    logging.info(f"fromDate: {dt_min.year}-{dt_min.month}-{dt_min.day}")
    logging.info(f"toDate: {dt_max.year}-{dt_max.month}-{dt_max.day}")
    params["daysToExpiration"] = 45
    req = "https://api.tdameritrade.com/v1/marketdata/chains"
    rsp = requests.get(req, params=params, headers=headers)
    if rsp.status_code != 200:
        logging.error(f"got bad status code: {rsp.status_code}")
        return None
    rsp_json = rsp.json()
    if rsp_json["status"] == "FAILED":
        logging.error("got FAILED status")
        return None
    #logging.info(rsp_json)
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
                        logging.info(f"skip put, underlying: {underlying} strike: {strike}")
                        continue
                elif description.endswith("Call"):
                    if underlying >= strike:
                        logging.info(f"skip call, underlying: {underlying} strike: {strike}")
                        continue
                else:
                    logging.info(f"unexpected description: {description}")
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
    logging.info(f"got {len(put_options)} put options")
    call_options = get_options(callMap, underlying)
    logging.info(f"got {len(call_options)} call options")

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
                logging.info(f"unexpected call last_strike: {last_strike} this_strike: {this_strike}")
                sys.exit(1)
            for k in range(len(put_list) - 1):
                pb = put_list[k]
                last_strike = pb["strike"]
                for l in range(k+1, len(put_list)):
                    ps = put_list[l]
                    this_strike = ps["strike"]
                    if this_strike <= last_strike:
                        logging.info(f"unexpected put last_strike: {last_strike} this_strike: {this_strike}")
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
    print("usage: python get_options.py [--skip-delta] [--sort prop] SYM")


#
# Main
#
if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
    print_usage()
    sys.exit(1)

symbols = []
ARGS["skip_delta"] = False
ARGS["sort_key"] = "et"
sort_keys = ("tc_ml", "et", "et_ml", "ml", "width", "tc_width", "et_width", "et_tc", "tc")

logging.basicConfig(format='LOG %(message)s', level=loglevel)

sort_key_arg = False
for argn in range(1, len(sys.argv)):
    argval = sys.argv[argn]
    if sort_key_arg:
        if argval not in sort_keys:
            print("sort key must be one of:", sort_keys)
            sys.exit(1)
        ARGS["sort_key"] = argval
        
        sort_key_arg = False
    elif argval.startswith('-'):
        if argval == "--skip-delta":
            ARGS["skip_delta"] = True
        elif argval == "--sort":
            sort_key_arg = True
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
    print("could not get any options")
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


for propname in sort_keys:
    candidates.sort(key = lambda candidate: candidate.get_prop(propname), reverse=True)
    rank = 1
    for candidate in candidates:
        candidate.set_rank(propname, rank)
        rank += 1


print("======================")
sort_key = ARGS["sort_key"]
candidates.sort(key = lambda candidate: candidate.get_prop(sort_key), reverse=True)

printCandidates(candidates)

 

