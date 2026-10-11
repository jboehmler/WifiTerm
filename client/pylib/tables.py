def maxwidth(listofstrings):
    """Return the length of the longest string in a list of strings"""
    return max([len(s) for s in listofstrings])


def maketable(mnlist, prelen=1, postlen=1, hbar="-", vbar="|"):
    """Return a list of [ [row00, row01, row02...row0n], [row10, row11,
    row12...row1n], ... [rowm0, rowm1, rowm2...rowmn]] as a row/col table string.

    mnlist[0][0]  mnlist[0][1]  mnlist[0][2]
    mnlist[1][0]  mnlist[1][1]  mnlist[1][2]
    mnlist[2][0]  mnlist[2][1]  mnlist[2][2]
    """
    numcols = len(mnlist)  # number of columns
    numrows = len(mnlist[0])  # number of rows
    colmaxs = []
    for m in range(numcols):
        # logging.debug("{}.".format())
        colmax = maxwidth(mnlist[m]) + prelen + postlen
        colmaxs.append(colmax)
    # build table string
    prepad = prelen * " "
    postpad = postlen * " "
    crlf = "\r\n"
    # twidth = sum(colmaxs) + numcols*(prelen + postlen) #add two for beginning and end vbars
    twidth = sum([(colwidth + prelen + postlen + 1) for colwidth in colmaxs]) + 1
    hbars = twidth * f"{hbar}" + crlf  # start with top horizontal bars
    ts = ""
    for row in range(numrows):  # rows
        tr = hbars  # horizontal bars above row
        for col in range(numcols):  # columns
            # tr += "{}{}{}{}".format(vbar, prepad, mnlist[col][row], postpad)
            tr += f"{vbar}{prepad}{mnlist[col][row]:{colmaxs[col]}}{postpad}"
            # logging.debug("{}.".format())
        tr += vbar + crlf  # end row
        # print(f"print row:  {tr}", end = "")
        ts += tr  # add row string to table string
    ts += hbars + crlf  # end table
    # print(ts)
    return ts


def testtable(rows=3, cols=5, maxwidth=5):
    from random import randrange
    from pprint import pprint

    testdata = []
    maxnum = 10**maxwidth - 1
    for row in range(rows):
        tr = []
        for col in range(cols):
            tr.append(str(randrange(maxnum)))
        testdata.append(tr)
    pprint(testdata)
    return testdata
