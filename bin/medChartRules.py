import re

def evaluate(func,row):
    pattern = r'\.(.*out\-of\-network.*?)\.'
    inNet=eval(row['In Network'])
    outNet=eval(row['Out of Network'])
    rowSpan,colSpan=inNet['id']['prntBbox'][1],inNet['id']['prntBbox'][2]
    mrgdCols=True if colSpan>1 else False
    lst = re.findall(pattern, row['In Network'])
    if lst and mrgdCols:
        return func(inNet['data']), func(lst[0])
    else:
        return func(inNet['data']), func(outNet['data'])

def getValue(row,isPrdHmo):
    if isPrdHmo:
        return val(eval(row['In Network'])['data'])
    else:
        return evaluate(val,row)

def getVisits(row,isPrdHmo):
    if isPrdHmo:
        return visits(eval(row['In Network'])['data'])
    else:
        return evaluate(visits, row)

def getDollarMax(row,isPrdHmo):
    if isPrdHmo:
        return dollarMax(eval(row['In Network'])['data'])
    else:
        return evaluate(dollarMax, row)

def val(inpStr):
    st = {"$0": "There is no coinsurance, copayment, or deductible for "}
    pattern = r'(\d+\.\d+|\d+)(?:%?\s*)(copayment|coinsurance)'
    l = re.findall(pattern, inpStr) #[(74,copayment)] $74.00
    if l:
        return '$' + '%.2f' % float(l[0][0]) if l[0][1] == 'copayment' else '%.2f' % float(l[0][0]) + '%'
    elif st['$0'] in inpStr:
        return '$0.00'

def visits(inpStr):
    pattern = r'(\d+|unlimited)(?: visits per plan year)'
    l = re.findall(pattern, inpStr)
    if l:
        if (l[0] == 'unlimited'):
            visits = '999.0'
        else:
            visits = '%.1f' % float(l[0])
    else:
        visits = ''
    return visits

def dollarMax(inpStr):
    pattern = r'(\d+)(?: annual calendar maximum per plan year)'
    l = re.findall(pattern, inpStr)
    if l:
        dollarMax = '$' + '%.2f' % float(l[0])
    else:
        dollarMax = ''
    return dollarMax
