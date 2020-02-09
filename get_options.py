import sys
import os
import time
import logging
from datetime import datetime
import requests

ARGS = {}

CS_DELTA_RANGE = (0.165, 0.32)
CB_DELTA_RANGE = (0.01, 0.25)
PS_DELTA_RANGE = (-0.32, -0.165)
PB_DELTA_RANGE = (-0.25, -0.01)

WINET_BOUND = 0.1
ET_BOUND = 0.0
ET_WIDTH_BOUND = 0
TC_WIDTH_BOUND = 0

SELL_SYMMETRY = 1 #0.12
TOTAL_SYMMETRY = 1 #0.25
WIDTH_SYMMETRY = 1 #1, no use

SORT_KEYS = ("tc_ml", "et", "et_ml", "ml", "width", "tc_width", "et_width", "et_tc", "tc", "symm", "winet")

NON_REVERSE_SORT = {"width", "ml", "symm"}

loglevel = logging.DEBUG  # DEBUG or INFO or ERROR


def check_delta_bound(delta, option_type=None, c_delta=None):
    if ARGS["skip_delta"]:
        return True
    if option_type == "cs":
        lbnd = CS_DELTA_RANGE[0]
        ubnd = CS_DELTA_RANGE[1]
    elif option_type == "cb":
        lbnd = CB_DELTA_RANGE[0]
        ubnd = CB_DELTA_RANGE[1]
        if c_delta:
            if c_delta > ubnd:
                ubnd = c_delta 
    elif option_type == "ps":
        lbnd = PS_DELTA_RANGE[0]
        ubnd = PS_DELTA_RANGE[1]
        if ubnd < -c_delta: 
            ubnd = -c_delta
        """
        lbnd = -c_delta - SELL_
        if lbnd < PS_DELTA_RANGE[0]:
            lbnd = PS_DELTA_RANGE[0]
        ubnd = -c_delta + SELL_
        if not ubnd < PS_DELTA_RANGE[1]:
            ubnd = PS_DELTA_RANGE[1]
        """
        logging.debug(f"ps: c_delta= {c_delta:.3f} lbnd= {lbnd:.3f} ubnd= {ubnd:.3f}")
    
    elif option_type == "pb":
        lbnd = PB_DELTA_RANGE[0]
        ubnd = PB_DELTA_RANGE[1]
        if c_delta:
            if c_delta > lbnd:
                lbnd = c_delta
    else:
        logging.error("invalid call type")
        sys.exit(1)
    
    logging.debug(f"check_delta: delta= {delta:.3f} lbnd= {lbnd:.3f} ubnd= {ubnd:.3f}")
    """
    if ubnd < lbnd:
        logging.warning("expected delta check upper bound to be greater than lower bound")
        return False
    """
    if lbnd <= delta and delta <= ubnd:
        return True

    return False

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

def descIsCall(desc):
    if desc.find("Call") > 0:
        return True
    else:
        return False

def descIsPut(desc):
    if desc.find("Put") > 0:
        return True
    else:
        return False
 

class Option:            
    def __init__(self, desc=None, delta=None, strike=None, price=None):
        self._desc = desc
        self._delta = delta
        self._strike = strike
        self._price = price

    def __str__(self):
        s = f"{self._desc} -- delta: {self._delta:.2f} price: {self._price:.2f} strike: {self._strike}"
        return s

    @property
    def desc(self):
        return self._desc

    @property
    def delta(self):
        return self._delta

    @property
    def price(self):
        return self._price

    @property
    def strike(self):
        return self._strike


class Candidate:
    def __init__(self, cs=None, cb=None, ps=None, pb=None, underlying=None):
        self._cs = cs
        self._cb = cb
        self._ps = ps
        self._pb = pb
        self._underlying = underlying
        self._tc_rank = [None, None]
        self._tc_ml_rank = [None, None]
        self._et_ml_rank = [None, None]
        self._et_rank = [None, None]
        self._et_width_rank = [None, None]
        self._et_tc_rank = [None, None]
        self._width_rank = [None, None]
        self._tc_width_rank = [None, None]
        self._ml_rank = [None, None]
        self._winet_rank = [None, None]
        self._symm_rank = [None, None]

        css = cs.strike
        cbs = cb.strike
        pss = ps.strike
        pbs = pb.strike
        csp = cs.price
        cbp = cb.price
        psp = ps.price
        pbp = pb.price
        csd = cs.delta
        cbd = cb.delta
        psd = ps.delta
        pbd = pb.delta 

        logging.info("******************")
        logging.info(f"Cand IC: {css}/{cbs}/{pss}/{pbs}" )
        logging.info(f"strike: {css:8.1f}  {cbs:8.1f}  {pss:8.1f}  {pbs:8.1f}" )
        logging.info(f"delta:  {csd:8.3f}  {cbd:8.3f}  {psd:8.3f}  {pbd:8.3f}" )
        logging.info(f"price:  {csp:8.3f}  {cbp:8.3f}  {psp:8.3f}  {pbp:8.3f}" )
        """
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
        """ 
        logging.info("******************")
        
        tc = csp - cbp + psp - pbp
        width = ((cbs - css) + (pss - pbs)) * 0.5
        symm = csd + cbd + psd + pbd

        logging.info(f"tc: {tc:.3f}")
        logging.info(f"width: {width:.3f}")
        
        logging.info(f"symm: {symm:.3f}")
        logging.info(f"cbs - css: {(cbs - css):.3f}")
        logging.info(f"pss - pbs: {(pss - pbs):.3f}")
      
        try:
            etc = tc * (1.0 - csd + psd) 
            delta_cc = tc * (csd - cbd)/(cbs - css)
            delta_pc = tc * (psd - pbd)/(pss - pbs) 
            delta_cd = csd - cbd - delta_cc
            delta_pd = psd - pbd - delta_pc 
            cd = cbs - css - tc
            pd = pss - pbs - tc
            """
            logging.info(f"d_cc: {delta_cc:.3f}")
            logging.info(f"d_pc:  {delta_pc:.3f}")   
            logging.info(f"d_cd: {delta_cd:.3f}")
            logging.info(f"d_pd: {delta_pd:.3f}")            
            logging.info(f"cd:  {cd:.3f}")            
            logging.info(f"pd: {pd:.3f}")
            """
            ecch = 0.5 * tc * delta_cc
            epch = -0.5 * tc * delta_pc
            ecdh = -0.5 * cd * delta_cd 
            epdh = 0.5 * pd * delta_pd 
            ecd = -cd * cbd 
            epd = pd * pbd 
            et = etc + ecch + ecdh + epch + epdh + ecd + epd
            winet = etc + ecch + epch
            """
            logging.info(f"etc: {etc:.3f}")
            logging.info(f"ecch: {ecch:.3f}")
            logging.info(f"epch: {epch:.3f}")
            logging.info(f"ecdh: {ecdh:.3f}")
            logging.info(f"epdh: {epdh:.3f}")
            logging.info(f"ecd: {ecd:.3f}")
            logging.info(f"epd: {epd:.3f}")
            """
            logging.info(f"et: {et:.3f}")
            logging.info(f"winet: {winet:.3f}")    

            tc_width = tc / width
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
            self._symm = abs(symm)
            self._winet = winet
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
            self._tc_ml = None
            self._symm = None
            self._winet = None

    
    def __str__(self):
        return f"{self._cs}/{self._cb}/{self._pb}/{self._ps}"

    def print_verbose(self, total=None, min_vals=None, max_vals=None):
        #print(candidate.keys())
        print() 

        print(f"IC: {self._cs.strike}/{self._cb.strike}/{self._ps.strike}/{self._pb.strike}" )
        print("cs:", self._cs)
        print("cb:", self._cb)
        print("ps:", self._ps)
        print("pb:", self._pb)
        print("----")
        
        if self._et:
            
            for propname in ("et", "tc", "width", "ml", "tc_width", "et_width", "et_tc", "symm", "winet"):
                propval = self.get_prop(propname)
                proprank = self.get_rank(propname)

                s = f"{propname}: {propval:.3f}"
                if proprank:
                    s += f" rank: {proprank}"
                if total:
                    s += f"/{total}"
                if min_vals and max_vals:
                    min_val = min_vals[propname]
                    max_val = max_vals[propname]
                    percent = int((propval - min_val) * 100.0 / (max_val - min_val))
                    s += f" [{min_val:.3f}-{max_val:.3f}] {percent}%"
                if "sort_key" in ARGS and ARGS["sort_key"] == propname:
                    s += " *"
                print(s)
            ssymm = self._cs.delta + self._ps.delta
            print(f"sell symm: {ssymm:.3f} ")


    
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

    @property
    def symm(self):
        return self._symm

    @property
    def symm_rank(self):
        return self._symm_rank   

    @property
    def winet(self):
        return self._winet

    @property
    def winet_rank(self):
        return self._winet_rank                   

    def set_tc_rank(self, rank):
        self._tc_rank = rank

    def set_et_width_rank(self, rank):
        self._et_width_rank = rank

    def set_et_tc_rank(self, rank):
        self._et_tc_rank = rank

    def set_symm_rank(self, rank):
        self._symm_rank = rank

    def set_winet_rank(self, rank):
        self._winet_rank = rank

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
        if propname == "symm":
            return self._symm     
        if propname == "winet":
            return self._winet 
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
        if propname == "symm":
            self._symm = value
            return  
        if propname == "winet":
            self._winet = value
            return                      
        logging.error(f"set_prop unexpected propname: [{propname}]")
        sys.exit(1)

    def get_rank(self, propname, byorder=False):
        if byorder:
            i = 1
        else:
            i = 0
        if propname == "tc_ml":
            return self._tc_ml_rank[i]
        if propname == "et":
            return self._et_rank[i]
        if propname == "et_ml":
            return self._et_ml_rank[i]
        if propname == "tc_width":
            return self._tc_width_rank[i]
        if propname == "et_width":
            return self._et_width_rank[i]
        if propname == "et_tc":
            return self._et_tc_rank[i]
        if propname == "tc":
            return self._tc_rank[i]
        if propname == "width":
            return self._width_rank[i]
        if propname == "ml":
            return self._ml_rank[i]
        if propname == "symm":
            return self._symm_rank[i]    
        if propname == "winet":
            return self._winet_rank[i]          
        logging.error(f"get_rank unexpected propname: [{propname}]")
        sys.exit(1)

    def set_rank(self, propname, value, byorder=False):
        if byorder:
            i = 1
        else:
            i = 0
        if propname == "tc_ml":
            self._tc_ml_rank[i] = value
            return
        if propname == "et":
            self._et_rank[i] = value
            return
        if propname == "et_ml":
            self._et_ml_rank[i] = value
            return
        if propname == "tc_width":
            self._tc_width_rank[i] = value
            return
        if propname == "et_width":
            self._et_width_rank[i] = value
            return
        if propname == "et_tc":
            self._et_tc_rank[i] = value
            return
        if propname == "tc":
            self._tc_rank[i] = value
            return
        if propname == "width":
            self._width_rank[i] = value
            return
        if propname == "ml":
            self._ml_rank[i] = value
            return
        if propname == "symm":
            self._symm_rank[i] = value
            return   
        if propname == "winet":
            self._winet_rank[i] = value
            return
        logging.error(f"set_rank unexpected propname: [{propname}]")
        sys.exit(1)

    



    def meets_requirements(self):
        logging.info(f"requirements check")

        if self._winet <= WINET_BOUND:
            logging.info(f"BAD winet: {self._winet}")
            return False

        if self._ps.strike - self._pb.strike <= self._tc:
            logging.info("BAD tail: put")
            return False   

        if self._cb.strike - self._cs.strike <= self._tc:
            logging.info("BAD tail: call")
            return False  

        if self._et <= ET_BOUND:
            logging.info(f"BAD et: {self._et:.3f} <= {ET_BOUND}")
            return False

        if not self.et_width >= ET_WIDTH_BOUND:
            logging.info(f"BAD et/width check: {self.et_width} < {ET_WIDTH_BOUND}")
            return False
        if not self.tc_width >= TC_WIDTH_BOUND:
            logging.info(f"BAD tc/width check: {self.tc_width} < {TC_WIDTH_BOUND}")
            return False
    
        return True

        
 

def printCandidates(candidates):
    total = len(candidates)
    propnames = ("tc_ml", "et", "et_ml", "ml", "width", "tc_width", "et_width", "et_tc", "tc", "symm", "winet")
    min_vals = {}
    max_vals = {}
    for candidate in candidates:
        for propname in propnames:
            val = candidate.get_prop(propname)
            if propname in min_vals:
                if val < min_vals[propname]:
                    min_vals[propname] = val
            else:
                min_vals[propname] = val
            if propname in max_vals:
                if val > max_vals[propname]:
                    max_vals[propname] = val
            else:
                max_vals[propname] = val
    for candidate in candidates:
        candidate.print_verbose(total=total, min_vals=min_vals, max_vals=max_vals)
        print("------------")

def get_chains(symbol, dt_min, dt_max):
    
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
                if descIsPut(description):
                    if underlying <= strike:
                        logging.info(f"skip put, underlying: {underlying} strike: {strike}")
                        continue
                elif descIsCall(description):
                    if underlying >= strike:
                        logging.info(f"skip call, underlying: {underlying} strike: {strike}")
                        continue
                else:
                    logging.info(f"unexpected description: {description}")
                    sys.exit(1)
                price = (option["bid"] + option["ask"])/2.0
                item = Option(desc=description, delta=delta, strike=strike, price=price)
                """
                if  delta >= PSS_RANGE[0] and delta <= PSS_RANGE[1]:
                    pss_options.append(item)
                elif delta >= PBS_RANGE[0] and delta <= PBS_RANGE[1]:
                    pbs_options.append(item)
                else:
                    print(f"skip put option: {description} delta: {delta}")
                """
                results.append(item)
    
    # remove the :nn from expire date 
    # e.g.: 2020-03-20:47 -> 2020-03-20
    n = expire_date.find(":")
    if n > 0:
        expire_date = expire_date[:n]
    return (results, expire_date)
    

def get_contracts(symbol, chains):
    underlying = chains["underlyingPrice"]
    putMap = chains["putExpDateMap"]
    callMap = chains["callExpDateMap"]
    
    (put_options, put_expire_date) = get_options(putMap, underlying)
    logging.info(f"got {len(put_options)} put options, expire_date: {put_expire_date}")
    (call_options, call_expire_date) = get_options(callMap, underlying)
    logging.info(f"got {len(call_options)} call options, expire_date: {call_expire_date}")
    if put_expire_date != call_expire_date:
        logging.error("expected put expire date to equal call expire date")
        sys.exit(1)
    # save options to file
    filename = f"data/{symbol}-{put_expire_date}.txt"
    with open(filename, 'w') as f:
        print(f"{symbol}, underlying: {underlying:12.3f}", file=f)
        desc =   "#           DESCRIPTION"
        delta =  "       DELTA"
        price =  "       PRICE"
        strike = "      STRIKE"

        print(f"{desc:40}{delta:12} {price:12} {strike:12}", file=f)
       
        for option in put_options:   
            desc = option.desc + ',' 
            print(f"{desc:40}{option.delta:12.3f},{option.price:12.3f},{option.strike:12.3f}", file=f)
        for option in call_options:  
            desc = option.desc + ','   
            print(f"{desc:40}{option.delta:12.3f},{option.price:12.3f},{option.strike:12.3f}", file=f)
 
    return {"underlying": underlying, "call": call_options, "put": put_options}   

def load_from_file(symbol, dt_min, dt_max):
    # search data files for valid file to load
    logging.info(f"load_file_file({symbol}, {dt_min}, {dt_max})")
    filenames = os.listdir("data")
    datafile = None
    for filename in filenames:
        if not filename.endswith(".txt"):
            continue
        filename = filename[:-4]  # drop extension
        n = filename.find('-')
        file_symbol = filename[:n]
        datestring = filename[(n+1):]
        if file_symbol != symbol:
            continue
         
        file_date = datetime.fromisoformat(datestring)
        if file_date > dt_min and file_date < dt_max:
            datafile = filename
            break
    if not datafile:
        logging.info("no datafile found")
        return None

    underlying = None
    calls = []
    puts = []
    with open("data/"+datafile+".txt") as f:
        line = f.readline().strip()
        # first line should be like: MMM, underlying:      158.630
        print("got line:", line)
        n = line.find(":")
        underlying = float(line[(n+1):])
        while line:
            line = f.readline().strip()
            if not line or line[0] == '#':
                continue
            fields = line.split(',')
            if len(fields) != 4:
                logging.error(f"unexpected line: {line}")
                continue
            desc = fields[0]
            delta = float(fields[1])
            price = float(fields[2])
            strike = float(fields[3])
            option = Option(desc=desc, delta=delta, strike=strike, price=price)
            if descIsPut(desc):
                puts.append(option)
            elif descIsCall(desc):
                calls.append(option)
            else:
                logging.error(f"unexpected desc: [{desc}]")

    logging.info(f"loaded {len(calls)} calls and {len(puts)} puts from file")
    return {"underlying": underlying, "call": calls, "put": puts}
        




def prelimination(cs=None, cb=None, ps=None, pb=None):  
                     
    logging.info(f"pre elimination check")
    logging.info(f"pree IC: {cs.strike:.1f}/{cb.strike:.1f}/{ps.strike:.1f}/{pb.strike:.1f}" )

    if cs.strike >= cb.strike:
        logging.info("BAD call strike: sell>buy")
        return False

    if pb.strike >= ps.strike:
        logging.info("BAD put strike: buy>sell")
        return False
    
    if ps.strike >= cs.strike:
        logging.info("BAD call/put strikes")
        return False

    if not ps.price >= pb.price:
        logging.info('BAD price: put sell < buy')
        return False

    if not cs.price >= cb.price:
        logging.info("BAD price: call sell < buy")
        return False
    
    if cb.strike - cs.strike > WIDTH_SYMMETRY * (ps.strike - pb.strike):
        logging.info(f"BAD width ratio call:put {cb.strike - cs.strike} : {ps.strike - pb.strike}")
        return False

    if ps.strike - pb.strike > WIDTH_SYMMETRY * (cb.strike - cs.strike):
        logging.info(f"BAD width ratio: put:call {ps.strike - pb.strike} : {cb.strike - cs.strike}")
        return False

    ssymm = cs.delta + ps.delta
    logging.info(f"sell symm = {ssymm:.3f}")
    if not abs(ssymm) < SELL_SYMMETRY:
        logging.info(f"BAD symmetry: sell delta: {abs(ssymm)} < {SELL_SYMMETRY}")
        return False

    symm = cs.delta + cb.delta + ps.delta + pb.delta
    if not abs(symm) < TOTAL_SYMMETRY:
        logging.info(f"BAD symmetry: over all symm = {ssymm:.3f} < {TOTAL_SYMMETRY}")
        return False

    return True

def get_ps(cs, ps, ps_1, ps1, underlying):
    logging.info(f"----ps: {ps.desc} delta: {ps.delta}")
    logging.info(f"get_ps -- cs: {cs} ps: {ps} ps_1: {ps_1}  ps1: {ps1}  underlying: {underlying}")
    logging.info(f"ps strike: {ps.strike} ps+1.strike: { ps1.strike}")
    logging.info(f"2underlying: {2*underlying-cs.strike} cs.strike: { cs.strike}")

    if (ps_1.strike < 2*underlying - cs.strike and 2*underlying - cs.strike <= ps.strike) or (ps.strike < 2*underlying - cs.strike and 2*underlying - cs.strike < ps1.strike):
        logging.info(f"picked by strike: ps.strike = {ps.strike} cs.strike = { cs.strike}")
        return True

    logging.info(f"delta ??? cs.delta = { cs.delta} ps_1.delta = {ps_1.delta} ps.delta = {ps.delta} ps1.delta = { ps1.delta}")

    if (-ps_1.delta < cs.delta and cs.delta <= -ps.delta) or (-ps.delta < cs.delta and cs.delta < -ps1.delta):
        logging.info(f"picked by delta: ps.delta = {ps.delta} cs.delta = { cs.delta}")
        logging.info(f"ps_1.delta = {ps_1.delta} ps1.delta = { ps1.delta}")
        return True

    if not check_delta_bound(ps.delta, option_type="ps", c_delta=cs.delta):
        logging.info("BAD bound: put sell delta")
        return False

    logging.info("get_ps returning True")
    return True

def get_candidates(contracts):
    candidates = []
    call_list = contracts["call"]
    put_list = contracts["put"]
    underlying = contracts["underlying"]
    total_count = 0
    meet_requirements_count = 0
    
    for i in range(len(call_list) - 1):
        cs = call_list[i]
        logging.info(f"--------cs: {cs.desc}, delta: {cs.delta}")
        if not check_delta_bound(cs.delta, option_type="cs"):
            logging.info("BAD bound: call sell delta")
            continue
        last_strike = cs.strike
        for j in range(i+1, len(call_list)):
            cb = call_list[j]
            logging.info(f"------cb: {cb.desc} delta: {cb.delta}")
            if not check_delta_bound(cb.delta, option_type="cb", c_delta=cs.delta):
                logging.info("BAD bound: call buy delta")
                continue
            this_strike = cb.strike
            
            if this_strike <= last_strike:
                logging.DEBUG(f"unexpected call last_strike: {last_strike} this_strike: {this_strike}")
                sys.exit(1)
            
            logging.info(f"search by k in {2}, {len(put_list) - 1}")
            for k in range(2, len(put_list) - 1):
                logging.info(f"---search by k in {k}")
                ps = put_list[k]
                if not get_ps(cs, ps, put_list[k-1], put_list[k+1], underlying):
                    logging.info(f"BAD ps: {ps.desc}")
                    continue
                """
                logging.info(f"----ps: {ps.desc} delta: {ps.delta}")
                logging.info(f"ps strike: {ps.strike} ps+1.strike: { put_list[k+1].strike}")
                logging.info(f"2underlying: {2*underlying-cs.strike} cs.strike: { cs.strike}")

                if (not ps.strike <= 2*underlying - cs.strike < put_list[k+1].strike) and (not put_list[k-1].strike <= 2*underlying - cs.strike < ps.strike):
                    if not check_delta_bound(ps.delta, option_type="ps", c_delta=cs.delta):
                        logging.info("BAD bound: put sell delta")
                        continue
                """
                last_strike = ps.strike
                for l in range(0, k):
                    pb = put_list[l]
                    logging.info(f"--pb: {pb.desc} delta: {pb.delta} ps.strike: {ps.strike}")
                    if not check_delta_bound(pb.delta, option_type="pb", c_delta=ps.delta):
                        logging.info("BAD bound: put buy delta")
                        continue
                    this_strike = pb.strike
                    if this_strike >= last_strike:
                        logging.info(f"unexpected put last_strike: {last_strike} this_strike: {this_strike}")
                        sys.exit(1)

                    logging.info(f"pre IC: {cs.strike}/{cb.strike}/{ps.strike}/{pb.strike}")
                    if True or prelimination(cs=cs, cb=cb, pb=pb, ps=ps):
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
    print("usage: python get_options.py [--skip-delta] [--sort prop] [--reload] SYM")


#
# Main
#
if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
    print_usage()
    sys.exit(1)

symbols = []
reload = False
ARGS["skip_delta"] = False
ARGS["sort_key"] = "et"

# setup logging
root = logging.getLogger()
root.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(loglevel)
formatter = logging.Formatter('%(levelname)s: %(message)s')
handler.setFormatter(formatter)
#logging.basicConfig(format='LOG %(message)s', level=loglevel)
root.addHandler(handler)

sort_key_arg = False
for argn in range(1, len(sys.argv)):
    argval = sys.argv[argn]
    if sort_key_arg:
        if argval not in SORT_KEYS:
            print("sort key must be one of:", SORT_KEYS)
            sys.exit(1)
        ARGS["sort_key"] = argval
        
        sort_key_arg = False
    elif argval.startswith('-'):
        if argval == "--skip-delta":
            ARGS["skip_delta"] = True
        elif argval == "--reload":
            reload = True
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
seconds_in_day = 24.0 * 60.0 * 60.0
exp_target_min = time.time() + 41.0 * seconds_in_day
dt_min = datetime.fromtimestamp(exp_target_min)
exp_target_max = time.time() + 60.0 * seconds_in_day
dt_max = datetime.fromtimestamp(exp_target_max)
    
contracts = None
if not reload:
    # see if we can load from previous file
    contracts = load_from_file(symbol, dt_min, dt_max)

if not contracts:
    chains = get_chains(symbol, dt_min, dt_max)
    if not chains:
        print("could not get any options")
        sys.exit(1)
    contracts = get_contracts(symbol, chains)

for k in ("call", "put"):
    options = contracts[k]
    print(k, len(options))
    for option in options:
        print(option.desc, option.delta)

for k in ("call", "put"):
    options = contracts[k]
    if len(options) == 0:
        print("no candidates!")
        sys.exit(0)

candidates = get_candidates(contracts)
print("got", len(candidates), "candidates")
print("======================")


for propname in SORT_KEYS:
    print("sorting by:", propname)
    if propname in NON_REVERSE_SORT:
        reverse = False
    else:
        reverse = True
    candidates.sort(key = lambda candidate: candidate.get_prop(propname), reverse=reverse)
    rank = 1
    order = 1
    prev = None
    for candidate in candidates:
        candidate.set_rank(propname, order, byorder=True)
        val = candidate.get_prop(propname)
        if prev:
            if abs(val - prev) > 0.001:
                rank = order
        candidate.set_rank(propname, rank)
        order += 1
        prev = val


print("======================")
sort_key = ARGS["sort_key"]
print(f"sorting by: [{sort_key}]")
candidates.sort(key = lambda candidate: candidate.get_rank(sort_key,byorder=True))


printCandidates(candidates)
 