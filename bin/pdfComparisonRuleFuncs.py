import re
def applyRegex(inpStr,argDi):
    regex=argDi['regex']
    subs=argDi['subs']
    inpStr=re.sub(bytes(regex.encode('utf-8')),subs.encode('utf-8'),inpStr.encode('utf-8')).decode('utf-8')
    return inpStr.strip()
