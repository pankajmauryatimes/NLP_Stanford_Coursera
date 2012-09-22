import sys
import os
import re
import pprint

e_pat1 = r'([\d\w\.-]+)[ \(\[-]*@[ \)\]-]*([\d\w \.\(\)\[\]_;-]+) *(org|com|edu|net|gov)+\b'
e_pat2 = r'([\d\w\.-]+)[ \(\[]+(at|where)[ \)\]]+([\d\w \.\(\)\[\]-_;]+) *(org|com|edu|net|gov)+\b'
# for unicode version of @
e_pat3 = r'([\d\w\.-]+) *(&#x40;) *([\d\w \.\(\)\[\]-_;]+) *(org|com|edu|net|gov)+\b'
e_pat4 = r'([\d\w\.-]+)[ \(\[-]*@[ \)\]-]*([\d\w \.\(\)\[\]_;-]+)\.([\d\w\.-]+)\b'
e_pat5 = r'([\d\w\.-]+)[ \(\["&;]*followed by[ \w\)\];"&]*@[ \)\]]*([\d\w \.\(\)\[\]-_;]+) *(org|com|edu|net|gov)+\b'

p_pat1 = r'\+*1[ \)\-]*(\d+)[ \)\-]*(\d+)[ \-]*(\d+)\b(?!/)'
p_pat2 = r'(?<!=)\b(\d+)[ \)\-\.]*(\d+)[ \-\.]*(\d+)\b(?!/)'

"""Get rid of space, "dot", and things like that."""
def process(st):
    res = re.sub(r" +(dot|dom|dt) +", r".", st, flags=re.I)
    res = re.sub(r" +", r".", res)
    res = re.sub(r";", r".", res)
    #res = re.sub(r"-|=", r"", res)
    return res

def contain_special(st):
    match = re.findall(r"dot|dom|\.| |;", st, re.I)
    return len(match)

def likely_phone(st):
    match = re.findall(r'phone|contact|tel|call|fax|office|home|ph\.', st, re.I)
    return len(match)

def special_judge_phone(st):
    """Words that might imply appearance of phone numbers"""
    likely_words = ['phone', 'contact', 'tel', 'call', 'fax',
                    'office', 'home', 'ph.', '@']
    has_likely_words = False
    for word in likely_words:
        if word in st:
            has_likely_words = True
            break
    match = re.findall(r'\bhref|\bhttp|\bsrc[ =]*', st, re.I)
    if len(match) and not has_likely_words:
        return False
    """Another special judge"""
    match = re.findall(r'template|mso|list|id', st, re.I)
    return len(match) <= 1

""" 
TODO
This function takes in a filename along with the file object (actually
a StringIO object at submission time) and
scans its contents against regex patterns. It returns a list of
(filename, type, value) tuples where type is either an 'e' or a 'p'
for e-mail or phone, and value is the formatted phone number or e-mail.
The canonical formats are:
     (name, 'p', '###-###-#####')
     (name, 'e', 'someone@something')
If the numbers you submit are formatted differently they will not
match the gold answers

NOTE: ***don't change this interface***, as it will be called directly by
the submit script

NOTE: You shouldn't need to worry about this, but just so you know, the
'f' parameter below will be of type StringIO at submission time. So, make
sure you check the StringIO interface if you do anything really tricky,
though StringIO should support most everything.
"""
def process_file(name, f):
    # note that debug info should be printed to stderr
    # sys.stderr.write('[process_file]\tprocessing file: %s\n' % (path))
    res = []
    for line in f:
        """email"""
        if ('Apache' in line) and ('Server' in line) and ('Port' in line):
            continue # special judge
        matches = re.findall(e_pat1, line, re.I)
        matches.extend(re.findall(e_pat2, line, re.I))
        matches.extend(re.findall(e_pat3, line, re.I))
        matches.extend(re.findall(e_pat5, line, re.I))
        for m in matches:
            email = m[0] + '@'
            if len(m) == 4: # at / where / unicode @
                if (not contain_special(m[2])):
                    continue
                processed = process(m[2])
                raw_domain = processed + m[3]
            elif len(m) == 3: # @, e_pat5
                if (not contain_special(m[1])):
                    continue
                processed = process(m[1])
                raw_domain = processed + m[2]
            domain = re.sub(r"[\(\[\)\] ]+", r"", raw_domain, flags=re.I)
            email += domain
            res.append((name,'e',email))
        
        matches = re.findall(e_pat4, line, re.I)
        for m in matches:
            if '-' not in m[2]:
                continue
            first = second = third = ""
            first = re.sub("-", "", m[0])
            second = re.sub("-", "", m[1])
            third = re.sub("-", "", m[2])
            email = first + '@' + second + '.' + third
            res.append((name, 'e', email))




        """phone"""
        matches = re.findall(p_pat1, line)
        matches.extend(re.findall(p_pat2, line))
        for m in matches:
            """special judge"""
            raw_phone = m[0] + m[1] + m[2]
            if len(raw_phone) != 10:
                continue
            if not special_judge_phone(line):
                continue
            #if ('-' not in line) and (' ' not in line) and ('(' not in line) and ('[' not in line) and (not likely_phone(line)):
#            if not likely_phone(line):
#                continue

            phone = m[0] + '-' + m[1] + '-' + m[2]
            res.append((name, 'p', phone))

    return res

"""
You should not need to edit this function, nor should you alter
its interface as it will be called directly by the submit script
"""
def process_dir(data_path):
    # get candidates
    guess_list = []
    for fname in os.listdir(data_path):
        if fname[0] == '.':
            continue
        path = os.path.join(data_path,fname)
        f = open(path,'r')
        f_guesses = process_file(fname, f)
        guess_list.extend(f_guesses)
    return guess_list

"""
You should not need to edit this function.
Given a path to a tsv file of gold e-mails and phone numbers
this function returns a list of tuples of the canonical form:
(filename, type, value)
"""
def get_gold(gold_path):
    # get gold answers
    gold_list = []
    f_gold = open(gold_path,'r')
    for line in f_gold:
        gold_list.append(tuple(line.strip().split('\t')))
    return gold_list

"""
You should not need to edit this function.
Given a list of guessed contacts and gold contacts, this function
computes the intersection and set differences, to compute the true
positives, false positives and false negatives.  Importantly, it
converts all of the values to lower case before comparing
"""
def score(guess_list, gold_list):
    guess_list = [(fname, _type, value.lower()) for (fname, _type, value) in guess_list]
    gold_list = [(fname, _type, value.lower()) for (fname, _type, value) in gold_list]
    guess_set = set(guess_list)
    gold_set = set(gold_list)

    tp = guess_set.intersection(gold_set)
    fp = guess_set - gold_set
    fn = gold_set - guess_set

    pp = pprint.PrettyPrinter()
    #print 'Guesses (%d): ' % len(guess_set)
    #pp.pprint(guess_set)
    #print 'Gold (%d): ' % len(gold_set)
    #pp.pprint(gold_set)
    print 'True Positives (%d): ' % len(tp)
    pp.pprint(tp)
    print 'False Positives (%d): ' % len(fp)
    pp.pprint(fp)
    print 'False Negatives (%d): ' % len(fn)
    pp.pprint(fn)
    print 'Summary: tp=%d, fp=%d, fn=%d' % (len(tp),len(fp),len(fn))

"""
You should not need to edit this function.
It takes in the string path to the data directory and the
gold file
"""
def main(data_path, gold_path):
    guess_list = process_dir(data_path)
    gold_list =  get_gold(gold_path)
    score(guess_list, gold_list)

"""
commandline interface takes a directory name and gold file.
It then processes each file within that directory and extracts any
matching e-mails or phone numbers and compares them to the gold file
"""
if __name__ == '__main__':
    if (len(sys.argv) != 3):
        print 'usage:\tSpamLord.py <data_dir> <gold_file>'
        sys.exit(0)
    main(sys.argv[1],sys.argv[2])
