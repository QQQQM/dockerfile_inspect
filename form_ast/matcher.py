import ast, json
import bashlex
import collections
import ast1, errors, helpconstants

class matchgroup(object):
    '''a class to group matchresults together

    we group all shell results in one group and create a new group for every
    command'''
    def __init__(self, name):
        self.name = name
        self.results = []

    def __repr__(self):
        return '<matchgroup %r with %d results>' % (self.name, len(self.results))

class matchresult(collections.namedtuple('matchresult', 'start end text match')):
    @property
    def unknown(self):
        return self.text is None

matchwordexpansion = collections.namedtuple('matchwordexpansion',
                                            'start end kind')

class matcher(ast1.Nodevisitor):
    def __init__(self, s):
        self.s = s
        self.functions = set()
        self._prevoption = self._currentoption = None
        self.expansions = []
        self.groups = [matchgroup('shell')]
        self.compoundstack = []
        self.groupstack = [(None, self.groups[-1], None)]
    
    def _generatecommandgroupname(self):
        existing = len([g for g in self.groups if g.name.startswith('command')])
        return 'command%d' % existing
    
    @property
    def matches(self):
        '''return the list of results from the most recently created group'''
        return self.groupstack[-1][1].results
    
    @property
    def manpage(self):
        group = self.groupstack[-1][1]
        # we do not have a manpage if the top of the stack is the shell group.
        # this can happen if the first argument is a command substitution
        # and we're not treating it as a "man page not found"
        if group.name != 'shell':
            return group.manpage

    def unknown(self, token, start, end, kind):
        # print('nothing to do with token ', token)
        return matchresult(start, end, token, kind)
    
    def visitcommand(self, node, parts):
        assert parts

        # look for the first WordNode, which might not be at parts[0]
        idxwordnode = bashlex.ast.findfirstkind(parts, 'word')
        if idxwordnode == -1:
            print('no words found in command (probably contains only redirects)')
            return

        wordnode = parts[idxwordnode]

        # check if this refers to a previously defined function
        if wordnode.word in self.functions:
            print('word ', wordnode , 'is a function, not trying to match it or its '
                        'arguments')

            # first, add a matchresult for the function call
            mr = matchresult(wordnode.pos[0], wordnode.pos[1], 
                            helpconstants._functioncall % wordnode.word, None)
            self.matches.append(mr)

            # this is a bit nasty: if we were to visit the command like we
            # normally do it would try to match it against a manpage. but
            # we don't have one here, we just want to take all the words and
            # consider them part of the function call
            for part in parts:
                # maybe it's a redirect...
                if part.kind != 'word':
                    self.visit(part)
                else:
                    # this is an argument to the function
                    if part is not wordnode:
                        mr = matchresult(part.pos[0], part.pos[1],
                                        helpconstants._functionarg % wordnode.word,
                                        None)
                        self.matches.append(mr)

                        # visit any expansions in there
                        for ppart in part.parts:
                            self.visit(ppart)

            # we're done with this commandnode, don't visit its children
            return False
        self.startcommand(node, parts, None)
    
    def startcommand(self, commandnode, parts, endword, addgroup=True):
        # print('startcommand commandnode=',commandnode,' \nparts=', parts, ', \nendword=',endword ,', \naddgroup=', addgroup)
        idxwordnode = bashlex.ast.findfirstkind(parts, 'word')
        assert idxwordnode != -1

        wordnode = parts[idxwordnode]
        if wordnode.parts:
            print('node %r has parts (it was expanded), no point in looking'
                        ' up a manpage for it' % wordnode)

            if addgroup:
                mg = matchgroup(self._generatecommandgroupname())
                mg.manpage = None
                mg.suggestions = None
                self.groups.append(mg)
                self.groupstack.append((commandnode, mg, endword))

            return False

        startpos, endpos = wordnode.pos

        # try:
        #     mps = self.findmanpages(wordnode.word)
        #     # we consume this node here, pop it from parts so we
        #     # don't visit it again as an argument
        #     parts.pop(idxwordnode)
        # except errors.ProgramDoesNotExist as e:
        #     if addgroup:
        #         # add a group for this command, we'll mark it as unknown
        #         # when visitword is called
        #         print('no manpage found for %r, adding a group for it' %
        #                     wordnode.word)

        #         mg = matchgroup(self._generatecommandgroupname())
        #         mg.error = e
        #         mg.manpage = None
        #         mg.suggestions = None
        #         self.groups.append(mg)
        #         self.groupstack.append((commandnode, mg, endword))
 
        #     return False

        # manpage = mps[0]
        # idxnextwordnode = bashlex.ast.findfirstkind(parts, 'word')

        # # check the next word for a possible multicommand if:
        # # - the matched manpage says so
        # # - we have another word node
        # # - the word node has no expansions in it
        # if manpage.multicommand and idxnextwordnode != -1 and not parts[idxnextwordnode].parts:
        #     nextwordnode = parts[idxnextwordnode]
        #     try:
        #         multi = '%s %s' % (wordnode.word, nextwordnode.word)
        #         logger.info('%r is a multicommand, trying to get another token and look up %r', manpage, multi)
        #         mps = self.findmanpages(multi)
        #         manpage = mps[0]
        #         # we consume this node here, pop it from parts so we
        #         # don't visit it again as an argument
        #         parts.pop(idxnextwordnode)
        #         endpos = nextwordnode.pos[1]
        #     except errors.ProgramDoesNotExist:
        #         logger.info('no manpage %r for multicommand %r', multi, manpage)

        # create a new matchgroup for the current command
        # mg = matchgroup(self._generatecommandgroupname())
        # mg.manpage = manpage
        # mg.suggestions = mps[1:]
        # self.groups.append(mg)
        # self.groupstack.append((commandnode, mg, endword))

        # self.matches.append(matchresult(startpos, endpos,
        #                     manpage.synopsis or helpconstants.NOSYNOPSIS, None))

        # self.groups[0].results.append(matchresult(node.pos[0], node.pos[1], helptext, None))
        # return True
        mg = matchgroup(self._generatecommandgroupname())
        mg.error = "no manpage"
        mg.manpage = None
        mg.suggestions = None
        self.groups.append(mg)
        self.groupstack.append((commandnode, mg, endword))
        return False
    
    def visitredirect(self, node, input, type, output, heredoc):
        print('the rediretion is:', type)
        try:
            self.matches.append(self.unknown(output.word, output.pos[0], output.pos[1], node.kind))
        except:
             self.matches.append(self.unknown(output, node.pos[0], node.pos[1], node.kind))
        return

    def visitcommandsubstitution(self, node, command):
        kind = self.s[node.pos[0]]
        substart = 2 if kind == '$' else 1

        # start the expansion after the $( or `
        self.expansions.append(matchwordexpansion(node.pos[0] + substart,
                                                  node.pos[1] - 1,
                                                  'substitution'))

        # do not try to match the child nodes
        return False
    
    def visitassignment(self, node, word):
        helptext = helpconstants.ASSIGNMENT
        self.groups[0].results.append(matchresult(node.pos[0], node.pos[1], helptext, None))

    def visitfunction(self, node, name, body, parts):
        self.functions.add(name.word)

        def _iscompoundopenclosecurly(compound):
            first, last = compound.list[0], compound.list[-1]
            if (first.kind == 'reservedword' and last.kind == 'reservedword' and
                first.word == '{' and last.word == '}'):
                return True

        # if the compound command we have there is { }, let's include the
        # {} as part of the function declaration. normally it would be
        # treated as a group command, but that seems less informative in this
        # context
        if _iscompoundopenclosecurly(body):
            # create a matchresult until after the first {
            mr = matchresult(node.pos[0], body.list[0].pos[1],
                            helpconstants._function, None)
            self.groups[0].results.append(mr)

            # create a matchresult for the closing }
            mr = matchresult(body.list[-1].pos[0], body.list[-1].pos[1],
                            helpconstants._function, None)
            self.groups[0].results.append(mr)

            # visit anything in between the { }
            for part in body.list[1:-1]:
                self.visit(part)
        else:
            beforebody = bashlex.ast.findfirstkind(parts, 'compound') - 1
            assert beforebody > 0
            beforebody = parts[beforebody]

            # create a matchresult ending at the node before body
            mr = matchresult(node.pos[0], beforebody.pos[1],
                            helpconstants._function, None)
            self.groups[0].results.append(mr)

            self.visit(body)

        return False
    
    def visitpipe(self, node, pipe):
        print('the pipe is:', pipe)
        self.matches.append(self.unknown(pipe, node.pos[0], node.pos[1], node.kind))
        return

    def visitword(self, node, word):
        def attemptfuzzy(chars):
            m = []
            if chars[0] == '-':
                tokens = [chars[0:2]] + list(chars[2:])
                considerarg = True
            else:
                tokens = list(chars)
                considerarg = False

            pos = node.pos[0]
            prevoption = None
            for i, t in enumerate(tokens):
                op = t if t[0] == '-' else '-' + t
                option = self.find_option(op)
                if option:
                    if considerarg and not m and option.expectsarg:
                        print('option', option, ' expected an arg, taking the rest too')
                        # reset the current option if we already took an argument,
                        # this prevents the next word node to also consider itself
                        # as an argument
                        self._currentoption = None
                        return [matchresult(pos, pos+len(chars), option.text, None)]

                    mr = matchresult(pos, pos+len(t), option.text, None)
                    m.append(mr)
                # if the previous option expected an argument and we couldn't
                # match the current token, take the rest as its argument, this
                # covers a series of short options where the last one has an argument
                # with no space between it, such as 'xargs -r0n1'
                elif considerarg and prevoption and prevoption.expectsarg:
                    pmr = m[-1]
                    mr = matchresult(pmr.start, pmr.end+(len(tokens)-i), pmr.text, None)
                    m[-1] = mr
                    # reset the current option if we already took an argument,
                    # this prevents the next word node to also consider itself
                    # as an argument
                    self._currentoption = None
                    break
                else:    
                    m.append(self.unknown(t, pos, pos+len(t)))
                pos += len(t)
                prevoption = option
            return m
        def _visitword(node, word):
            if not self.manpage:
                # print('the word is: %r', word)
                # print('inside an unknown command, giving up on %r', word)
                self.matches.append(self.unknown(word, node.pos[0], node.pos[1], node.kind))
                return

            print('trying to match token: %r', word)

            self._prevoption = self._currentoption
            if word.startswith('--'):
                word = word.split('=', 1)[0]
            option = self.find_option(word)
            if option:
                print('found an exact match for %r: %r', word, option)
                mr = matchresult(node.pos[0], node.pos[1], option.text, None)
                self.matches.append(mr)

                # check if we splitted the word just above, if we did then reset
                # the current option so the next word doesn't consider itself
                # an argument
                if word != node.word: 
                    self._currentoption = None
            else:
                word = node.word

                # check if we're inside a nested command and this word marks the end
                if isinstance(self.groupstack[-1][-1], list) and word in self.groupstack[-1][-1]:
                    print('token %r ends current nested command', word)
                    self.endcommand()
                    mr = matchresult(node.pos[0], node.pos[1], self.matches[-1].text, None)
                    self.matches.append(mr)
                elif word != '-' and word.startswith('-') and not word.startswith('--'):
                    print('looks like a short option')
                    if len(word) > 2:
                        print("trying to split it up")
                        self.matches.extend(attemptfuzzy(word))
                    else:
                        self.matches.append(self.unknown(word, node.pos[0], node.pos[1]))
                elif self._prevoption and self._prevoption.expectsarg:
                    print("previous option possibly expected an arg, and we can't"
                            " find an option to match the current token, assuming it's an arg")
                    ea = self._prevoption.expectsarg
                    possibleargs = ea if isinstance(ea, list) else []
                    take = True
                    if possibleargs and word not in possibleargs:
                        take = False
                        print('token %r not in list of possible args %r for %r',
                                    word, possibleargs, self._prevoption)
                    if take:
                        if self._prevoption.nestedcommand:
                            print('option %r can nest commands', self._prevoption)
                            if self.startcommand(None, [node], self._prevoption.nestedcommand, addgroup=False):
                                self._currentoption = None
                                return

                        pmr = self.matches[-1]
                        mr = matchresult(pmr.start, node.pos[1], pmr.text, None)
                        self.matches[-1] = mr
                    else:
                        self.matches.append(self.unknown(word, node.pos[0], node.pos[1]))
                else:
                    if self.manpage.partialmatch:
                        print('attemping to do a partial match')

                        m = attemptfuzzy(word)
                        if not any(mm.unknown for mm in m):
                            print('found a match for everything, taking it')
                            self.matches.extend(m)
                            return

                    if self.manpage.arguments:
                        if self.manpage.nestedcommand:
                            print('manpage %r can nest commands', self.manpage)
                            if self.startcommand(None, [node], self.manpage.nestedcommand, addgroup=False):
                                self._currentoption = None
                                return

                        d = self.manpage.arguments
                        k = list(d.keys())[0]
                        print('got arguments, using %r', k)
                        text = d[k]
                        mr = matchresult(node.pos[0], node.pos[1], text, None)
                        self.matches.append(mr)
                        return

                    # if all of that failed, we can't explain it so mark it unknown
                    self.matches.append(self.unknown(word, node.pos[0], node.pos[1]))
        _visitword(node, word)

    def match(self):
        print("matching string", self.s)

        # limit recursive parsing to a depth of 1
        self.ast = bashlex.parser.parsesingle(self.s, expansionlimit=1, strictmode=False)
        print(self.ast.dump())
        if self.ast:
            self.visit(self.ast)
            # assert len(self.groupstack) == 1, 'groupstack should contain only shell group after matching'

            # if we only have one command in there and no shell results/expansions,
            # reraise the original exception
            if (len(self.groups) == 2 and not self.groups[0].results and
                self.groups[1].manpage is None and not self.expansions):
                raise self.groups[1].error
        else:
            print('no AST generated for ', self.s)
        
        return self.groups
    
    def match_json(self):
        # print("++++++++++++  matching string", self.s)
        self.ast = bashlex.parser.parsesingle(self.s, expansionlimit=1, strictmode=False)
        # print(self.ast.dump())
        if self.ast:
            self.visit(self.ast)
        return self.groups


