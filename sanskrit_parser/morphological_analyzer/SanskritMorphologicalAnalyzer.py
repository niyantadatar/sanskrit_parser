#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
  Morphological Analyzer for Sanskrit Sentences. 


'''
from __future__ import print_function
import sanskrit_parser.base.SanskritBase as SanskritBase
import sanskrit_parser.lexical_analyzer.SanskritLexicalAnalyzer as SanskritLexicalAnalyzer
import constraint

import logging
logger = logging.getLogger(__name__)

need_lakara=False

def getSLP1Tagset(n):
    return set(map(lambda x: x.transcoded(SanskritBase.SLP1),list(n[1])))

# Lakaras
_lakaras=set(['law','liw','luw','lrw','low','laN','liN','luN','lfN','law-karmaRi','liw-karmaRi','luw-karmaRi','lrw-karmaRi','low-karmaRi','laN-karmaRi','liN-karmaRi','luN-karmaRi','lfN-karmaRi'])
# Disallowed last padas
_ldis = set(['samAsapUrvapadanAmapadam','upasargaH'])
# Vacanas
_vacanas=set(['ekavacanam','dvivacanam','bahuvacanam'])
# Puruzas
_puruzas=['praTamapuruzaH','maDyamapuruzaH','uttamapuruzaH']
prathama='praTamAviBaktiH'
# Lingas
_lingas=set(['puMlliNgam','napuMsakaliNgam','strIliNgam'])
_sankhya=set(['saNKyA'])
# Samastapada former parts
_samastas=set(['samAsapUrvapadanAmapadam'])
# tiGanta vibhaktis
_vibhaktis=set(['praTamAviBaktiH','dvitIyAviBaktiH','tritIyAviBaktiH',
                'caturTIviBaktiH','paNcamIviBaktiH','zazWIviBaktiH',
                'saptamIviBaktiH','saMboDanaviBaktiH'])

# Rules for morphological analyzer
# Only one lakara
def oneLakara(*nodes):
    ''' Only one Lakara is allowed '''
    # lakaras in SLP1
    global need_lakara
    l=0
    for n in nodes:
        nset=getSLP1Tagset(n)
        if not(_lakaras.isdisjoint(nset)):
            l=l+1
    # Variable to enforce a lakara
    if need_lakara:
        return l==1
    else:
        return l<=1 

# Last pada cannot be an upasarga or samasapurvapada
def lastWord(*nodes):
    n = nodes[-1]
    nset=getSLP1Tagset(n)
    r = _ldis.isdisjoint(nset)
    logger.debug(nset)
    return r

# Upasarga must be before a verb
def upasarga(*nodes):
    r = True 
    for ix,n in enumerate(nodes):
        nset=getSLP1Tagset(n)
        if set(['upasargaH']) <= nset:
            r = r and (not _lakaras.isdisjoint(getSLP1Tagset(nodes[ix+1])))
    return r
    
# padas in prathamA must match purusha / vacana of lakara
def prathamA(*nodes):
    ''' padas in prathamA ('kartr'/karman) must match the purusha / vacana of lakara'''
    r=True
    vacana=None
    for n in nodes:
        nset=getSLP1Tagset(n)
        # Pick the first lakara
        if not(_lakaras.isdisjoint(nset)):
            vacana=nset.intersection(_vacanas)
            logger.debug("Found Lakara vacana:{}".format(vacana))
            assert len(vacana)==1, "Only one vacana allowed: {}".format(list(vacana))
            vacana=list(vacana)[0]
            puruza=nset.intersection(_puruzas)
            logger.debug("Found Lakara puruza:{}".format(puruza))
            assert len(puruza)==1, "Only one puruza allowed: {}".format(list(puruza))
            puruza=list(puruza)[0]
    # No lakara found
    if vacana is None:
        return not need_lakara
    for n in nodes:
        nset=getSLP1Tagset(n)
        if prathama in nset:
            mvacana=nset.intersection(_vacanas)
            logger.debug("Found PrathamA vacana:{}".format(mvacana))
            assert len(mvacana)==1, "Only one mvacana allowed: {}".format(list(mvacana))
            mvacana=list(mvacana)[0]
            r = r and (mvacana==vacana)
            if puruza==_puruzas[2]:
                logger.debug('PrathamA stem:{}'.format(n[0]))
                r = r and n[0]=='asmad'
            elif puruza==_puruzas[1]:
                logger.debug('PrathamA stem:{}'.format(n[0]))
                r = r and n[0]=='yuzmad'
    return r


# all padas in same case must match in linga and vacana
def vibhaktiAgreement(*nodes):
    ''' All padas in same vibhakti must agree in linga and vacana '''
    maps={}
    for n in nodes:
        nset=getSLP1Tagset(n)
        vibhakti = _vibhaktis.intersection(nset) 
        if vibhakti:
            assert len(vibhakti)==1, "Only one vibhakti allowed: {}".format(list(vibhakti))
            logger.debug("Found vibhakti:{}".format(vibhakti))
            vibhakti=list(vibhakti)[0]
            vacana=nset.intersection(_vacanas)
            logger.debug("Found vacana:{}".format(vacana))
            assert len(vacana)==1, "Only one vacana allowed: {}".format(list(vacana))
            vacana=list(vacana)[0]
            linga=nset.intersection(_lingas)
            logger.debug("Found linga:{}".format(linga))
            if len(linga)==0:
                sankhya=nset.intersection(_sankhya)
                if sankhya: # Is "Sankhya" type (kati etc.)
                    continue
            assert len(linga)==1, "Only one linga allowed: {}".format(list(linga))
            linga=list(linga)[0]
            slv = set([linga,vacana])
            if vibhakti in maps:
                if maps[vibhakti] != slv:
                    logger.debug("Unequal:{} {}".format(maps[vibhakti],slv))
                    return False
                else:
                    logger.debug("Equal:{} {}".format(maps[vibhakti],slv))
            else:
                maps[vibhakti]=slv
                logger.debug("Map: {} : {}".format(vibhakti,slv))
    return True
                             
# samAsa constituents must be followed by another samasa constiuent or subanta
def samasarules(*nodes):
    ''' samasa constituents must be followed by tiGantas 
        (or other samasa constituents)
    '''
    r=True
    l=len(nodes)-1
    for ix,n in enumerate(nodes):
        nset=getSLP1Tagset(n)
        if not _samastas.isdisjoint(nset):
            if ix==l:
                return False
            else:
                nset1=getSLP1Tagset(nodes[ix+1])
                if _samastas.isdisjoint(nset1):
                    r = r and (not _vibhaktis.isdisjoint(nset1))
    return r


# upasarga rules
# karmapravcanIya rules


class SanskritMorphologicalAnalyzer(SanskritLexicalAnalyzer.SanskritLexicalAnalyzer):
    """ Singleton class to hold methods for Sanksrit morphological analysis. 
    
    """
    def __init__(self):
        super(SanskritMorphologicalAnalyzer,self).__init__()

    def constrainPath(self,path):
        ''' Apply Morphological Constraints on path

        Params:
            path(list): List of SanskritObjects (tagged)
        '''
        _ncache={}
        vlist=[]
        def _uniq(s):
            if s not in _ncache:
                _ncache[s]=0
                return s
            else:
                _ncache[s]=_ncache[s]+1
                return s+"_"+str(_ncache[s])
        # Ensure we have tags
        for p in path:
            assert p.tags, "No tags for {}".format(p)
        # Solver
        problem = constraint.Problem()
        for p in path:
            v=_uniq(str(p))
            vlist.append(v)
            logger.debug("Added Variable {} {}".format(v,p.tags))
            problem.addVariable(v,p.tags)
        problem.addConstraint(oneLakara)
        problem.addConstraint(lastWord,vlist)
        problem.addConstraint(upasarga,vlist)
        problem.addConstraint(prathamA,vlist)
        problem.addConstraint(samasarules,vlist)
        problem.addConstraint(vibhaktiAgreement,vlist)
        s=problem.getSolutions()
        return s
    
if __name__ == "__main__":
    from argparse import ArgumentParser
    def getArgs():
        """
          Argparse routine. 
          Returns args variable
        """
        # Parser Setup
        parser = ArgumentParser(description='Lexical Analyzer')
        # String to encode
        parser.add_argument('data',nargs="?",type=str,default="astyuttarasyAMdishidevatAtmA")
        # Input Encoding (autodetect by default)
        parser.add_argument('--input-encoding',type=str,default=None)
        # Need a lakara
        parser.add_argument('--need-lakara',action='store_true')
        parser.add_argument('--debug',action='store_true')
        parser.add_argument('--max-paths',type=int,default=10)
        return parser.parse_args()

    def main():
        global need_lakara
        args=getArgs()
        print("Input String:", args.data)
        need_lakara = args.need_lakara
        
        if args.debug:
            logging.basicConfig(filename='SanskritMorphologicalAnalyzer.log', filemode='w', level=logging.DEBUG)
        else:
            logging.basicConfig(filename='SanskritMorphologicalAnalyzer.log', filemode='w', level=logging.INFO)
        s=SanskritMorphologicalAnalyzer()
        if args.input_encoding is None:
            ie = None
        else:
            ie = SanskritBase.SCHEMES[args.input_encoding]
        i=SanskritBase.SanskritObject(args.data,encoding=ie)
        print("Input String in SLP1:",i.transcoded(SanskritBase.SLP1))
        import datetime
        print("Start Split:", datetime.datetime.now())
        graph=s.getSandhiSplits(i,tag=True,debug=args.debug)
        print("End DAG generation:", datetime.datetime.now())
        if graph:
            splits=graph.findAllPaths(max_paths=args.max_paths,debug=args.debug)
            print("End pathfinding:", datetime.datetime.now())
            print("Splits:")
            for sp in splits:
                print("Lexical Split:",sp)
                p=s.constrainPath(sp)
                if p:
                    print("Valid Morphologies")
                    for pp in p:
                        print([(spp,pp[str(spp)]) for spp in sp])
                else:
                    print("No valid morphologies for this split")
        else:
            print("No Valid Splits Found")
            return
            
    main()

