# -*- coding: utf-8 -*-
"""
Created on Sun Apr 22 2018

@author: GTasse

Edited on Thu May 17 02:40:59 2018

@author: Evelyn Stamey
"""

"""
As a first step, we need to establish a connection to the "contextionary" database
"contextionary" database is a database of phrases and their contexts organized into multiple
tables including:
    - "context": list of more than two thousand contexts or topics or activities
    - "phrase": list of all phrases or length varying from 1 to 5 words
    - "phrase origin": list of the document origin of each phrase
    - "document:" list of all documents used to collect the phrases
    - "phrase meaning": list of the meaning of each contextual phrase by context
    - "phrase vector space": list of the frequency of each phrase by context
    - "context axis": list of the coordinates of of each context axis in the word vector space
    - "phrase distance to context": list of the distances from each  phrase to each context
    - "context semantic field": list of all the context lexical set
    - "phrase semantic field": list of all the phrases related to contextual phrases
    - "shared word": list of each pair of context phrases sharing a common word
    - "context spelling similarity": list of each pair of contexts having a similar spelling
    - "phrase spelling similarity": list of each pair of context phrases having a similar spelling
    - "phrase weight by context": list of the relative weights of each phrase in each context
    - 
"""
from psycopg2 import connect 
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT 
#from psycopg2.extensions import ISOLATION_LEVEL_DEFAULT
import config
import numpy as np

con = connect(dbname=config.DATABASE['dbname'],
              user=config.DATABASE['user'],
              password=config.DATABASE['password'])
con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT) 
#con.set_isolation_level(ISOLATION_LEVEL_DEFAULT) 


class WordVectorSpace(object):
   
    def __init__(self, distancePercentile, bondingIndexPercentile):
        
        """
        WordVectoSpace class builds a vector space of phrases. The base of the space is the set of all independent contexts.
        The dimension of the space is the number of independent contexts (an independent context is a context with 0 child). 
        A phrase is represented by a vector in that space and its coordinates are the relative frequency 
        of the phrase within each independent context.
        The vector space is made of:
            - vectors: words
            - axis: contexts
        """
 
        
        """
        WordVectorSpace class uses 6 class variables:
            - contexts: dictionary of contexts {contextID:context object} from the contextionary database context table
            - phrases: dictionary of phrases {phraseID:phrase object} from the contextionary database phrase table
            - phraseVectorSpaceMatrix: Array -- phrase row -independent context column -- of the phrase vectors into the
            word vector space
            - contextAxisMatrix: Array -- regular context row - independent context column -- of the context axis coordinates
            into the word vector space
            - distanceToContextMatrix: Array -- phrase row - regular context column - of the phrase distance to each context
            - dimension: number of independent contexts (any context with 0 child)
        """
        self.contexts = dict()
        self.phrases = dict()
        self.phraseVectorSpaceMatrix = None
        self.contextAxisMatrix = None
        self.distanceToContextMatrix = None
        self.phraseWeightByContextMatrix = None
        cur = con.cursor()
        cur.execute(""" SELECT count(*) FROM context WHERE "context_children_id" = %s; """, (['0']),)                
        self.dimension = cur.fetchone()[0]
        print("dimension")
        print(self.dimension)
        self.distancePercentile = distancePercentile
        self.bondingIndexPercentile = bondingIndexPercentile
        
        self.phraseCountPerDocument=dict()
        self.phraseCountPerDocument_length=dict()
        self.phraseCountPerContext=dict()
        self.contextVolumeByPhraseLength=dict()
        self.contextDatabase=dict()
        
        # importing csv module 
        import csv
        
    
        with open('phraseCountPerDocument.csv', 'r') as csv_file:
            reader = csv.reader(csv_file)    
            self.phraseCountPerDocument = {(int(rows[0]),int(rows[1]),int(rows[3])):int(rows[4]) for rows in reader}            
       
        with open('phraseCountPerDocument.csv', 'r') as csv_file:
            reader = csv.reader(csv_file)    
            self.phraseCountPerContext = {(int(rows[0]),int(rows[1])):0 for rows in reader}
            
        for dockey in self.phraseCountPerDocument.keys():
            phrasekey=dockey[:-1]
            self.phraseCountPerContext[phrasekey]+=self.phraseCountPerDocument[dockey]
        
        
        """
        context volume by phrase length
        """
        with open('phraseCountPerDocument.csv', 'r') as csv_file:
            reader = csv.reader(csv_file)    
            self.phraseCountPerDocument_length = {(int(rows[0]),int(rows[2]),int(rows[1]),int(rows[3])):int(rows[4]) for rows in reader}            
       
        with open('phraseCountPerDocument.csv', 'r') as csv_file:
            reader = csv.reader(csv_file)    
            self.contextVolumeByPhraseLength = {(int(rows[0]),int(rows[2])):0 for rows in reader}
            
        for dockey in self.phraseCountPerDocument_length.keys():
            volumekey=dockey[:-2]
            self.contextVolumeByPhraseLength[volumekey]+=self.phraseCountPerDocument_length[dockey]
             
        print("PhraseCountPerDocument")
        print(self.phraseCountPerDocument)
        print("PhraseCountPerContext")
        print(self.phraseCountPerContext)
        print("PhraseCountPerDocument_length")
        print(self.phraseCountPerDocument_length)
        print("contextVolumeByPhraseLength")
        print(self.contextVolumeByPhraseLength)
        
        """
        context csv file contains all the context attribute with:
        key column = context_id (primary key)
        column 0   = context_immediate_parent_id
        column 1   = context_name
        column 2   = context_children_id
        column 3   = context_picture
        column 4   = context_level
        column 5   = icindex
        column 6   = rcindex
        """
        with open('context.csv', 'r') as csv_file:
            reader = csv.reader(csv_file)    
            next(reader)
            self.contextDatabase = {int(rows[0]):[int(rows[1]),rows[2],rows[3],rows[4],int(rows[5]),int(rows[6]),int(rows[7])] for rows in reader}  
  
        
        """
        phrase csv file contains all the phrase attributes with:
        key column = phrase_id (primary key)
        column 0   = phrase_text
        column 1   = phrase_length
        column 2   = red_flag
        column 3   = phrase_index
        """
        with open('phrase.csv', 'r') as csv_file:
            reader = csv.reader(csv_file)    
            next(reader)
            self.phraseDatabase = {int(rows[0]):[rows[1],int(rows[2]),int(rows[3]),int(rows[4])] for rows in reader}  
  
        
        
            
  
        
        """
        WordVectorSpace class performs 14 major sequential tasks:
            - createContextDictionary: adds entries into the --contexts-- dictionary
            - createPhraseDictionary: adds entries into the --phrases-- dictionary
            - buildPhraseVectorSpaceMatrix: creates the word/phrase vectors
            - buildContextAxisMatrix: creates the context axis
            - build distanceToContextMatrix: calculates the distance from each vector of the space (phrase)
            to each axis (context)
            - createContextLexicalSet: finds the lexical set (context phrases) of each context
            - createPhraseLexicalSet: finds the lexical set (related phrases) of each contextual phrase
            - updateSharedWord: finds pairs of contextual words that share a word together
            - updateContextSpellingSimilarity: find pairs of contexts that have similar spellings 
            - updatePhraseSpellingSimilarity: find pairs of contextual phrases that have similar spellings
            - buildPhraseWeightByContextMatrix: 
        """
        
        
        """
        phraseIDList: list of IDs of phrases as recorded in the --phrase-- table of the --contextionary-- database
        """
        
        
        print("create context dictionary....")
        self.createContextDictionary() 
        
        
    
        print("create phrase dictionary....")
        self.createPhraseDictionary() 
        print("create phrase vector space matrix....")
        self.buildPhraseVectorSpaceMatrix()
        print("build context axis matrix....")
        self.buildContextAxisMatrix()
        print("build distance to context matrix....")
        self.buildDistanceToContextMatrix()

        print("create context lexical set....")
        self.createContextLexicalSet()
        print("create phrase lexical set....")
        self.createPhraseLexicalSet()

        
        print("build phrase weight by context matrix....")
        self.buildPhraseWeightByContextMatrix()

        
        print("update shared word....")
        self.updateSharedWord()
        print("update context spelling similarity....")
        self.updateContextSpellingSimilarity()
        print("create phrase spelling similarity....")
        self.updatePhraseSpellingSimilarity()
        print("update frequency distance table....")
        self.updateFrequencyDistanceTable()
        

    """
    createContextDictionary method creates a Python dictionary {key:value} in which each entry will have
    a context ID as a key and a Context object as a value.
    The context ID comes from the contextionary database context table.
    The Context object is created using the Class Context with 8 parameters: contextName, contextID, ancestorsID, independence boolean,
    ICIndex, RCIndex, dimension, phraseCount
    Note that a context immediate parent is the first ancestor of that context. The immediate parent of the
    immediate parent is the second ancestor and so on.
    """
    def createContextDictionary(self):
        
                
        
        """
        ICIndex = Independent Context Index. This denotes the position of an independent context
        in the list of independent contexts.
        RCIndex = Regular Context Index. This denotes the position of a regular context (dependent or independen)
        in the list of regular contexts.
        """
        defaultIndex=-1
        ICIndex = 0
        RCIndex = 0

        """
        contextIDList: list of IDs of contexts as recorded in the context table of the --contextionary-- database
        """
        
        
        
        
        """
        For each context having phrases of varying lengths 1, 2, 3, etc.....
        to total number of phrases per length is updated in the phraseCount dictionary
        """
            
            
        cur = con.cursor()    
        cur.execute(""" SELECT DISTINCT "phrase_length" FROM phrase;""")
        phraseLengths = cur.fetchall()
        phraseLengths = list([x[0] for x in phraseLengths])
        
        """
        Adding all contexts into context volume by phrase length
        """
        for contextID in self.contextDatabase.keys():
            for phraseLength in phraseLengths:
                if (contextID,phraseLength) not in self.contextVolumeByPhraseLength.keys():
                    self.contextVolumeByPhraseLength.update({(contextID,phraseLength):0})
        
        """
        Defining the list on contexts that contain documents
        """
        #phraseMeaningContextID=list(set([x[0] for x in self.phraseCountPerContext.keys()]))
            
        #print("List of contexts that contain documents")
        #print(phraseMeaningContextID)
            
      

        """
        For each context in the database list of contexts, a context object is created from the class Context
        """
        
        for contextID in self.contextDatabase.keys():
 
            """
            contextName is the name of the context as recorded in the context table of the contextionary database
            """
            contextName=self.contextDatabase[contextID][1]
            contextChildrenID=self.contextDatabase[contextID][2]
    
                        
            """
            Create the list of ancestors ID of a context called --ancestorsID--.
            In the ancestors list you will have the immediate parent ID, the ID of its immediate
            parent up to the most remote ancestor of all contexts: "Human activity".
            """   
            ancestorsID = []
            cipID = self.contextDatabase[contextID][0]
            
            while cipID != -1:
                ancestorsID.append(cipID)
                cipID = self.contextDatabase[cipID][0] 
            
           
           
            
            
            if contextChildrenID == '0':
                """
                If the context is independent (0 child), then an independent context object is created
                """
                self.contextDatabase[contextID][5]=ICIndex
                self.contextDatabase[contextID][6]=RCIndex
                self.contexts.update({contextID: Context(contextName, contextID,
                                                         ancestorsID, True,
                                                         ICIndex, RCIndex,
                                                         self.dimension,
                                                         self.contextVolumeByPhraseLength)})
                ICIndex += 1

            else:
                """
                If the context is not independent (has at least 1 child), then a dependent context object is created
                """
                self.contextDatabase[contextID][5]=defaultIndex
                self.contextDatabase[contextID][6]=RCIndex
                self.contexts.update({contextID: Context(contextName, contextID,
                                                         ancestorsID, False,
                                                         defaultIndex, RCIndex,
                                                         self.dimension,self.contextVolumeByPhraseLength)})
            RCIndex += 1
        
        
        #print("Context Database - check icindex and rcindex")
        #print(self.contextDatabase) 
        
        
        
        """
        For each independent context, calculate its axis coordinates in the vector space
        """
        for contextID in self.contexts.keys():
            context=self.contexts[contextID]                     
            contextChildrenID=self.contextDatabase[contextID][2]

            if contextChildrenID == '0':
                        
                ICIndex = context.getICIndex()
                ancestorsID = context.getAncestorsID()
                ancestors = []
                for id in ancestorsID:
                    """
                    NEW LINE
                    """
                    self.contexts[id].addIndependentDescendantsID(contextID)
                    
                    ancestors.append(self.contexts[id])
                context.updateAxis(ICIndex,ancestors)

                """
                UPDATE ANCESTORS PHRASE COUNT
                """
                context.updateAncestorPhraseCount(context.getPhraseCount(),ancestors)
        #print("Context Human activity and its independent descendants")
        #print(contextID)
        #print(self.contexts[1].getIndependentDescendantsID())
        #print("Context Belief and its independent descendants")
        #print(self.contexts[2].getIndependentDescendantsID())

    """
    createPhraseDictionary method creates a Python dictionary {key:value} in which each entry will have
    a phrase ID as a key and a Phrase object as a value.
    The phrase ID comes from the contextionary database phrase table.
    The Phrase object is created using the Class Phrase with 6 parameters: phraseName, phraseID, 
    phraseLength,index,phraseCountPerContext,documentPerContext
    """
    
    def createPhraseDictionary(self):
        
        """
        index = This denotes the position of a phrase in the list of all phrases.
        """

        index = 0

        """
        phraseIDList: list of IDs of phrases as recorded in the --phrase-- table of the --contextionary-- database
        """
        
        highCountPhrase=dict((k, v) for k, v in self.phraseCountPerContext.items() if v >=10)
        l=list(highCountPhrase)
        #print(l)
        phraseIDList=list(set([x[1] for x in l]))
        #print(phraseIDList)
        #cur = con.cursor()

        print("how many phrases should we deal with?")
        print(len(phraseIDList))
        
        """
        For each phrase in the database table of phrases, a phrase object is created from the class Phrase
        """
        
        compteur = 0
        
        """
        phrase csv file contains all the phrase attributes with:
        key column = phrase_id (primary key)
        column 0   = phrase_text
        column 1   = phrase_length
        column 2   = red_flag
        column 3   = phrase_index
        """
        
        """
        FOR-LOOP IS TOO LONG. NEED AN ALTERNATIVE. VECTORIZATION? MULTIPROCESSING?
        """
        for phraseID in phraseIDList:

            compteur += 1
            print("%s phrases out of %s"%(compteur,len(phraseIDList)))
            phraseText=self.phraseDatabase[phraseID][0]
            phraseLength=self.phraseDatabase[phraseID][1]
            self.phraseDatabase[phraseID][3]=index                  
            
            #phraseCountPerContext = dict()
            for contextID in self.contexts.keys():
                if (contextID,phraseID) not in self.phraseCountPerContext.keys():
                    self.phraseCountPerContext.update({(contextID,phraseID): 0})
                
            documentPerContext = [[]]*len(self.contexts)

            """
            For each context:
                - the count of the phrase is collected and updated in the phraseCountPerContext list.
                - then the documents of origin of the phrase are also gathered and updated in the documentPerContext list.
            """
            for contextID in self.contexts.keys():
                
                context = self.contexts[contextID]
                
                """
                Phrase count collection from the --phrase meaning-- database
                """
                #cur = con.cursor()
                #cur.execute(""" SELECT "phrase_count_per_context" FROM "phrase_meaning" WHERE "phrase_id" = %s AND "context_id" = %s; """, ([phraseID, contextID]))
                #count = cur.fetchall()
                #if count:
                #phraseCountPerContext.update({contextID: count[0][0]})
                if (contextID,phraseID) in self.phraseCountPerContext.keys():
                    """
                    if context is independent, the countpercontext of its ancestors should be
                    incremented by the count of the independent context
                    """       
                    for ancestorID in context.getAncestorsID():
                        ancestor = self.contexts[ancestorID]
                        self.phraseCountPerContext[(ancestor.getID(),phraseID)] += self.phraseCountPerContext[(contextID,phraseID)]

                """
                Document list collection from the --phrase origin-- database
                """ 
                #cur = con.cursor()
                #cur.execute("""SELECT "phrase_origin"."document_id" FROM "phrase_origin", document WHERE "phrase_id" = %s AND "context_id"=%s  AND "phrase_origin"."document_id"="document"."document_id"; """, ([phraseID, contextID]))
                #selection = cur.fetchall()
                
                
                selection=[]
                for key in self.phraseCountPerDocument.keys():
                    if key[0]==contextID and key[1]==phraseID:
                        selection.append(key[2])
                documentPerContext[context.getRCIndex()] =selection
                #self.phraseCountPerDocument[(contextID,phraseID,documentID)]
                
                
                for ancestorID in context.getAncestorsID():
                    ancestor = self.contexts[ancestorID]
                    documentPerContext[ancestor.getRCIndex()] = set(documentPerContext[ancestor.getRCIndex()]).union(selection)
                
                """
                if selection:
                    documentPerContext[context.getRCIndex()] = selection
                    for ancestorID in context.getAncestorsID():
                            ancestor = self.contexts[ancestorID]
                            documentPerContext[ancestor.getRCIndex()] = set(documentPerContext[ancestor.getRCIndex()]).union(selection)
                """
            """
            Creation of the phrase object which is updated in the phrase dictionary
            """
            self.phrases.update({phraseID: Phrase(phraseText, phraseID,
                                                     phraseLength, index,
                                                     self.phraseCountPerContext,
                                                     documentPerContext, self.contexts)})
            index += 1
            

            phrase = self.phrases[phraseID]
            flag = phrase.getFlag()
            self.phraseDatabase[phraseID][2]=flag
            #########

    """
    buildPhraseVectorSpaceMatrix method creates an array containing each phrase vector with coordinates
    on each independent context axis.
    """ 
    def buildPhraseVectorSpaceMatrix(self):    
   
        import numpy as np 

        """
        Create a matrix p lines, c columns using the database --contextionary--. The matrix name is self.phraseVectorSpaceMatrix
        p is the number (count) of "phrase ID" of the phrase table
        c is the number (count) of "context ID" of the context table where "context children ID" = 0
        The line i of the matrix corresponds to the phrase of the self.phrases dictionary with index = i
        The column j of the matrix corresponds to the context of the self.contexts dictionary with index = j
        Each cell of the matrix of line i and column j contains the following relative frequency ij: 
        phrase i getCountPerContext[j] / context j getPhraseCount[phrase i.getPhraseLength]
        """

        p = 0
        c = 0
        
        #cur = con.cursor()
        #cur.execute("""DELETE FROM "phrase_vector_space";""")
        
        independentContextID=list(set([k for k in self.contextDatabase.keys() if self.contextDatabase[k][2]=="0"]))
        
        #print("independentContextID")
        #print(independentContextID)
        #cur = con.cursor()
        #cur.execute(""" SELECT "context_id" FROM "context" WHERE "context_children_id" = %s; """, (['0']))
        #independentContextID = cur.fetchall()
        #independentContextID = list([x[0] for x in independentContextID])
        #print("independent ContextID: %s"% independentContextID)
        p = len(self.phrases) #i
        c = len(independentContextID) #j
        
        self.phraseVectorSpaceMatrix = np.zeros((p,c))
        
        for phraseID in self.phrases.keys():
            phrase = self.phrases[phraseID]
            i = phrase.getIndex()
            for ICID in independentContextID:
                context = self.contexts[ICID]
                j = context.getICIndex()
                #k=context.getRCIndex()
                #self.phraseVectorSpaceMatrix[(i,j)]= phrase.getPhraseCountPerContext()[k]/(context.getPhraseCount()[phrase.getPhraseLength()])
                if self.contextVolumeByPhraseLength[(ICID,phrase.getPhraseLength())]==0:
                #if context.getPhraseCount()[phrase.getPhraseLength()] == 0:
                    self.phraseVectorSpaceMatrix[(i, j)] = 0
                else:
                    self.phraseVectorSpaceMatrix[(i, j)] = phrase.getPhraseCountPerContext(ICID)/(self.contextVolumeByPhraseLength[(ICID,phrase.getPhraseLength())])
                    
                    
        """
        Delete all existing entries of table "phrase vector space".
        Add entries phrase i, independent context j, phrase relative frequency ij
        """
        #cur = con.cursor()
        #cur.execute("""DELETE FROM "phrase_vector_space";""")
        
        for phraseID in self.phrases.keys():
            phrase = self.phrases[phraseID]
            i = phrase.getIndex()
            for ICID in independentContextID:
                context = self.contexts[ICID]
                j = context.getICIndex()
                #cur.execute("""INSERT INTO "phrase_vector_space" ("phrase_id", "context_id", "phrase_relative_frequency")
                #                VALUES (%s,%s,%s)""", ([phraseID, ICID, self.phraseVectorSpaceMatrix[(i,j)]]))

        print("Phrase vector space matrix")
        print (self.phraseVectorSpaceMatrix)
        print(np.sum(self.phraseVectorSpaceMatrix))
        
    
    """
    buildContextAxisMatrix method creates an array containing each phrase vector with coordinates
    on each independent context axis.
    It is designed to express each context as an axis in the phrase vector space.
    Any context is generated by the linear combination of one to more independent contexts.
    Example: context human activity axis will be (1,1,1,1,1,1,1,....) because it depends on all
    the independent contexts. The coordinate is either 0 or 1.
    """ 
    def buildContextAxisMatrix(self):  
          
        """
        The context axis matrix is created by combining the axis coordinates of each context
        """ 
        contextAxis = []
        import numpy as np   
        for contextID in self.contexts.keys():
            contextAxis.append(self.contexts[contextID].getAxis())
        self.contextAxisMatrix = np.array(contextAxis)
        
        #print("context axis matrix element size in byte and total size in MB")
        #print (self.contextAxisMatrix.itemsize)
        #print (self.contextAxisMatrix.itemsize * self.contextAxisMatrix.size/1000000)
  
        """
        Delete all existing entries of table "context axis".
        Insert entries context i, independent context j, context i coordinate on independent context j
        """
        #cur = con.cursor()
        #cur.execute("""DELETE FROM "context_axis";""")
        
        #print("Start inserting context axis coordinates into database")
        #cur = con.cursor()
        #cur.execute(""" SELECT "context_id" FROM "context" WHERE "context_children_id" = %s; """, (['0']))
        #independentContextID = cur.fetchall()
        #independentContextID = list([x[0] for x in independentContextID])
        #for contextID in self.contexts.keys():
        #   i = self.contexts[contextID].getRCIndex()
        #   for ICID in independentContextID:
        #       j = self.contexts[ICID].getICIndex()
        #       cur = con.cursor()
        #       cur.execute("""INSERT INTO "context_axis" ("context_id", "independent_context_id", "axis_coordinate")
        #       VALUES (%s,%s,%s)""", ([contextID, ICID, int(self.contextAxisMatrix[i][j])]))
        #print("Finish inserting context axis coordinates into database")
        
        print("Context axis matrix")
        print (self.contextAxisMatrix)
        
    
    """
    buildDistanceToContextMatrix creates an array containing each phrase distance to each context,
    dependent or independent. 
    The method also records the content of the matrix (distances) into the table "phrase distance to context"
    on the --contextionary-- database.
    Finally, the method calculates and assigns the lexical set boundary for each context. 
    """
    def buildDistanceToContextMatrix(self):  

        """
        Delete all existing entries of table "phrase_distance_to_context".
        """
        cur = con.cursor()
        cur.execute("""DELETE FROM "phrase_distance_to_context";""")

        """
        The matrix is updated with the distance between each phrase and each context
        """
        import numpy as np
        import time
        
        #p = len(self.phrases)
        #c = len(self.contexts)
        distancematricestarttime=time.time()
        
        #self.distanceToContextMatrix = np.zeros((p, c))


        normContextAxisMatrix = self.contextAxisMatrix / np.linalg.norm(self.contextAxisMatrix, axis=1).reshape(-1,1) ** 2
        self.distanceToContextMatrix=np.concatenate(np.apply_along_axis(self.calculateDistancePhraseToContext, 1, self.phraseVectorSpaceMatrix, self.contextAxisMatrix, normContextAxisMatrix), 0)
            
      
            
        distancematriceendtime=time.time()
        
        print("Time to build distanceToContextMatrix: %s" %(distancematriceendtime-distancematricestarttime))
        
        
        """
        Insert entries phrase i, context j, distance ij into the "phrase distance to context" table of the
        --contextionary-- database
        """    
        
        print("distance to context matrix")
        print(self.distanceToContextMatrix)
        """
        For each context, calculate and assign its lexical set boundary .
        The lexical set of a context represents a select list of phrases from
        all phrases used in the context. That select list is the group of phrases
        that are the closest in term of distance to the context. 
        The 10% closest phrases to the context will be defined as the context lexical set.
        This value is assumed and a lower or higher value can be chosen based on experience.
        The assumption made here is that about 19% of the words we use in a speech or a text are purely
        contextual and the rest is general. It can be argued that the actual number is higher and can
        be as high as 20%.
        The distance above which any phrase is not part of the lexical set is called
        the lexical set boundary and is calculate as the context phrases 10% distance percentile.
        """
        for contextID in self.contexts.keys():
                
            context = self.contexts[contextID]
            j = context.getRCIndex()
            
            distance = []
            for phraseID in self.phrases.keys():
                phrase = self.phrases[phraseID]
                i = phrase.getIndex()
      
                """
                if the phrase exists in the context
                """
                if phrase.getPhraseCountPerContext(contextID)>0:
                    distance.append(self.distanceToContextMatrix[i,j])
            
            if not distance:
                context.setLexicalSetBoundary(0)
            else:
                boundary = np.percentile(distance, self.distancePercentile)
                context.setLexicalSetBoundary(boundary)

    """
    The distance between a vector and an axis is simply the norm of the difference
    between that vector and its orthogonal projection on the axis
    """
    def calculateDistancePhraseToContext(self, phraseVectorRow, contextAxisMatrix, normContextAxisMatrix):
        
        # Using broadcast to compute th product each row for the contextAxisMatrix by
        # the prhaseVectorRow
        phraseProjection = contextAxisMatrix * normContextAxisMatrix.dot(phraseVectorRow).reshape(-1, 1)
        difference = phraseProjection - phraseVectorRow
        normVector = np.linalg.norm(difference, axis=1).reshape(1, -1)

        return normVector

    
    def buildHMatrix(self,row):
        
        R = np.array(row)
        R.shape = (len(row), 1)
        RT = R.T
        TRR = np.dot(RT, R)
        print(TRR)
        print(TRR.size)
        ITRR = np.linalg.inv(TRR)
        P = np.dot(R, ITRR)
        P = np.dot(P, RT)
        print("HMatrix")
        print(P)
        print(P.size)
        print("size in MB: %s" %(P.nbytes/1000000))

        return P



    

    def buildPhraseWeightByContextMatrix(self):
         
        """
        Delete all existing entries of table "phrase distance to context".
        """
        #cur = con.cursor()
        #cur.execute("""DELETE FROM "phrase_weight_by_context";""")
        
        import numpy as np
        #maxDistance=np.amax(self.distanceToContextMatrix)
        
        p = len(self.phrases)
        c = len(self.contexts)
        
        self.phraseWeightByContextMatrix = np.zeros((p, c))
        
        #maxDistance=np.amax(self.distanceToContextMatrix)
        maxFrequency = np.amax(self.phraseVectorSpaceMatrix)
      
        
        """
        FOR-LOOP IS TOO LONG. NEED AN ALTERNATIVE. VECTORIZATION? MULTIPROCESSING?
        I BELIEVE VECTORIZATION IS MORE APPROPRIATE AND ELEGANT
        """
        for contextID in self.contexts.keys():
            context = self.contexts[contextID]
            j = context.getRCIndex()
             
            #print("the context --%s-- has the following lexical set --%s--" %(context.getName(),context.getLexicalSet()))
            for phraseID in self.phrases.keys():
                phrase = self.phrases[phraseID]
                i = phrase.getIndex()
                phraseCountInContext = phrase.getPhraseCountPerContext(contextID)
                totalPhraseCount = self.contextVolumeByPhraseLength[(contextID,phrase.getPhraseLength())]
                
                if totalPhraseCount == 0:
                    frequency = 0
                else:
                    frequency = phraseCountInContext/totalPhraseCount
                if phrase in context.getLexicalSet().keys():
                    weight = 1
                    self.phraseWeightByContextMatrix[i][j] = weight
                else:                    
                    weight = frequency/maxFrequency
                    self.phraseWeightByContextMatrix[i][j] = weight

        """
        Insert entries phrase i, context j, weight ij into the "phrase weight by context" table of the
        --contextionary-- database
        """    

        #for phraseID in self.phrases.keys():
        #    i = self.phrases[phraseID].getIndex()
        #    for contextID in self.contexts.keys():
        #        j = self.contexts[contextID].getRCIndex()
        #        cur = con.cursor()
        #        cur.execute("""INSERT INTO "phrase_weight_by_context" ("phrase_id", "context_id", "phrase_weight")
        #        VALUES (%s,%s,%s)""", ([phraseID, contextID, self.phraseWeightByContextMatrix[i][j]]))

        
        """
        export phraseWeightByContextMatrix to json file
        """
        #import numpy
        
        a = np.asarray(self.phraseWeightByContextMatrix)
        np.savetxt("phraseWeightByContextMatrix.csv", a, delimiter=",")
        
        print(self.phraseWeightByContextMatrix)
        print(np.sum(self.phraseWeightByContextMatrix))
    
    """
    This method creates a dictionary {phrase:distance to context} that collects
    all the phrases deemed close to a particular context. This set is the lexical set
    also called here semantic field of a context.
    The method also reset the "context semantic field" table of the --contextionary-- database
    and records the lexical set entries by context 
    """
            
    def createContextLexicalSet(self):

        """
        Delete all existing entries of table "context semantic field".
        "context semantic field" table is a table consisting of 2 columns: context and phrase.
        To each context correspond all phrases that qualify as their lexical field.
        """
        cur = con.cursor()
        cur.execute("""DELETE FROM "context_phrase";""")

        """
        INDEPENDENT CONTEXTS METHODOLOGY
        Lexical set construction methodology with independent contexts.
        """
        
        independentContextID=list(set([k for k in self.contextDatabase.keys() if self.contextDatabase[k][2]=="0"]))
        

        for contextID in independentContextID:
            contextID = contextID[0]
            context = self.contexts[contextID]
            lexicalSet = dict()
            for phraseID in self.phrases.keys():
                phrase = self.phrases[phraseID]
                
                if phrase.getPhraseCrossPresenceOverContextChildren()[contextID] == 1:
                
                    d = self.distanceToContextMatrix[phrase.getIndex()][context.getRCIndex()]
                    if d <= context.getLexicalSetBoundary():
                        lexicalSet.update({phrase:d})
                        
                        """
                        Add entries context ID, phrase ID into the table "context semantic field".
                        """
                    
                        ######### revised 05/30/2018
                        cur = con.cursor()
                        cur.execute("""INSERT INTO "context_phrase" ("context_id", "phrase_id")
                        VALUES (%s,%s)""", ([contextID, phraseID]))
            context.setLexicalSet(lexicalSet)
        
        """
        DEPENDENT CONTEXTS METHODOLOGY
        Lexical set construction methodology with dependent contexts.
        """    
     
        dependentContextID=list(set([k for k in self.contextDatabase.keys() if self.contextDatabase[k][2]!="0"]))
        
        
        for phraseID in self.phrases.keys():
            #phraseID=phraseID[0]
            phrase = self.phrases[phraseID]
            for contextID in dependentContextID:
                contextID = contextID[0]
                context = self.contexts[contextID]
                ancestorsID = context.getAncestorsID()
                #lexicalSet=dict()
                if phrase.isSignificantlyPresentInContext(contextID):
                    belongsToLexicalSet = True
                    for ancestorID in ancestorsID:
                        if phrase.isSignificantlyPresentInContext(ancestorID):
                            belongsToLexicalSet = False
                    if belongsToLexicalSet:
                        cur = con.cursor()
                        cur.execute("""INSERT INTO "context_phrase" ("context_id", "phrase_id")
                        VALUES (%s,%s)""", ([contextID, phraseID]))
                        distance=self.distanceToContextMatrix[phrase.getIndex()][context.getRCIndex()]
                        #lexicalSet.update({phrase:d})
                        context.updateLexicalSet(phrase,distance)

    """
    createPhraseLexicalSet method creates a phrase lexical set (semantic field).
    A phrase lexical set is the list of phrases that relate to it (meaning, often found together in the same documents).
    The relation is context and document based.
    To identify which phrases qualify that definition, 4 variables are defined.
    Note that what we call context phrase is a phrase belonging to a context semantic field.
    contextPhraseDocumentCount is the number of documents a context phrase belongs to.
    relatedPhraseDocumentCount is the number of documents a phrase potentially related to the context phrase belongs to.
    sharedDocumentCount represents how many documents do the context phrase and the related phrase share together.
    All these 3 variables can be extracted from the "phrase origin" table.
    The fourth variable, phraseBondingIndex will be a calculated using the following formula:
    phraseBondingIndex = sharedDocumentCount/(contextPhraseDocumentCount+relatedPhraseDocumentCount-sharedDocumentCount)
    A value of 0 means that the 2 phrases are never encountered together in the same document.
    A value of 1 means that the 2 phrases are always seen together in all documents any is found.
    The method also reset the "phrase semantic field" table of the --contextionary-- database
    and records the lexical set entries by context 
    """
    def createPhraseLexicalSet(self):
        
        
        """
        Delete all existing entries of table "phrase semantic field".
        "phrase semantic field" table is a table consisting of 4 columns: context ID, context phrase ID,
        related phrase ID, phrase bonding index
        To each context correspond all context phrases of its lexical field. To each context phrase correspond
        all phrases related to it along with the strengh of their bonding/relation
        """   
    
        cur = con.cursor()
        cur.execute("""DELETE FROM "related_phrase";""")       
        
        contextPhraseDocumentCount=0
        relatedPhraseDocumentCount=0
        sharedDocumentCount=0
        phraseBondingIndex=0
       
        """
        For each context, the lexical set is explored and a bonding index is calculated
        between each pair of phrase within the lexical set. In that way, the terms related
        to any context phrase can be determines.
        """
        for contextID in self.contexts.keys():
            context = self.contexts[contextID]
            
            """
            Explore lexical set
            """
      
            counter = 0
            for contextPhrase in context.getLexicalSet().keys():
                    
                counter += 1
                
                if counter % 100 == 0:
                    print(contextPhrase.getText())
                    print(counter)
    
                contextPhrase.initializeLexicalSetByContext(len(self.contexts))                
                contextPhraseLexicalSet = dict()
                
                """
                Define contextPhraseDocumentCount by calculating its integer value from the
                "phrase origin" table
                """
                #counter2 = 0
                contextPhraseDocument = contextPhrase.getDocumentPerContext()[context.getRCIndex()]
                contextPhraseDocumentCount = len(contextPhraseDocument)
                
                for relatedPhrase in context.getLexicalSet().keys():
                    
                    """   
                    if contextPhrase is different from relatedPhrase. 
                    We do want to compare relatedPhrase to all other phrases except itself.
                    """   
                
                    if contextPhrase != relatedPhrase:

                        """
                        Under the if condition above, define relatedPhraseDocumentCount by calculating 
                        its integer value from the "phrase origin" table 
                        From "phrase origin" table, define sharedDocumentCount which is the number of documents
                        shared by the two phrases contextPhrase and relatedPhrase
                        Calculate phraseBondingIndex using the formula:
                        phraseBondingIndex = sharedDocumentCount/(contextPhraseDocumentCount+relatedPhraseDocumentCount-sharedDocumentCount)
                        Record the entry into contextPhrasLexicalSet with {key:value}={relatedPhrase:phraseBondingIndex}    
                        """

                        relatedPhraseDocument=relatedPhrase.getDocumentPerContext()[context.getRCIndex()]
                        relatedPhraseDocumentCount=len(relatedPhraseDocument)
                        
                        sharedDocument=set(contextPhraseDocument).intersection(relatedPhraseDocument)
                        sharedDocumentCount = len(sharedDocument)
                        
                        if(contextPhraseDocumentCount+relatedPhraseDocumentCount-sharedDocumentCount==0):
                        
                            print("SharedDocumentCount: %s" %sharedDocumentCount)
                            
                            print("context phrase: %s . related phrase: %s" %(contextPhrase.getText(),relatedPhrase.getText()))
                            
                            print("These 2 phrases share no document together.")
                            
                            print("contextPhraseDocumentCount: %s" %contextPhraseDocumentCount)
                            if contextPhraseDocumentCount==0:
                                print("context phrase appears in no document")
                            
                            print("relatedPhraseDocumentCount: %s" %relatedPhraseDocumentCount)
                            if relatedPhraseDocumentCount==0:
                                print("related phrase appears in no document")
                            
                            """
                            FIXING AN ANOMALY.
                            IF THE DATABASE INTEGRITY WAS COMPROMISED, IT WILL HAPPEN THAT contextPhraseDocumentCount=0
                            0 IS NOT A LOGICAL VALUE FOR THIS VARIABLE.
                            TO CORRECT THE ANOMALY, WE WILL ASSIGN AN INCORRECT BUT MORE PLAUSIBLE VALUE TO THE
                            VARIABLE AND THAT VALUE WILL BE 1.
                            THEREFORE, WE WILL NOT EXPECT A DIVISION BY ZERO ANYMORE.
                            """
                            contextPhraseDocumentCount=1
                        
                        
                        
                        
                        phraseBondingIndex = sharedDocumentCount/(contextPhraseDocumentCount+relatedPhraseDocumentCount-sharedDocumentCount)
                     
                        contextPhraseLexicalSet.update({relatedPhrase:phraseBondingIndex})
                        
                """
                Calculate the 90% percentile of the contextPhraseLexicalSet values.
                It is assumed here that 90% of the connections between a phrase and others are not strong enough.
                """
                #import numpy as np
                ######### revised 06/03/2018
                lst = list(contextPhraseLexicalSet.values())
                if lst:
                #########
                    boundary = np.percentile(list(contextPhraseLexicalSet.values()),self.bondingIndexPercentile)
                    contextPhrase.setLexicalSetBoundary(boundary)      
                    
                    """
                    Cut the contextPhraseSemanticField dictionary down to only the phrases with phraseBondingIndex > boundary
                    """
                
                    keepkeys = []
                    for key in contextPhraseLexicalSet.keys():
                        if contextPhraseLexicalSet[key] > boundary:
                            keepkeys.append(key)
                    
                    contextPhraseLexicalSet = {k: contextPhraseLexicalSet[k] for k in keepkeys}
                         
                    """
                    After the semanticField dictionary has been filtered down, it can now be added into the lexicalSetByContext list
                    """
                    
                    contextPhrase.updateLexicalSetByContext(contextPhraseLexicalSet,context.getRCIndex())
                    
                    """
                    Update the "phrase semantic field" with the following entries:
                    context ID, context Phrase ID, related Phrase ID and phrase bonding strength
                    Note that related Phrase ID and phrase bonding strength will simply come from above
                    contextPhraseSemanticField dictionary while context ID and context Phrase ID are fixed and known
                    """
                
                    for relatedPhrase in contextPhraseLexicalSet.keys():
                        cur = con.cursor()
                        cur.execute("""INSERT INTO "related_phrase" ("context_id", "context_phrase_id", "related_phrase_id", "phrase_bonding_index")
                        VALUES (%s,%s, %s,%s)""", ([contextID, contextPhrase.getPhraseID(), relatedPhrase.getPhraseID(), contextPhraseLexicalSet[relatedPhrase]]))

    ######### revised 06/04/2018
    def updateSharedWord(self):
        
        # Delete all existing entries in shared word table
        cur = con.cursor()
        cur.execute("""DELETE FROM "shared_word";""")
        
        # Get complete list of phrase IDs which have phrase length >= 2
        # GUY: Threshold should be 2 instead of 1 right?
        phraseLengthThreshold = 2
        cur = con.cursor()
        cur.execute(""" SELECT "phrase_id" FROM "phrase" WHERE "phrase_length" >= %s AND "red_flag"=0; """, ([phraseLengthThreshold]))
        allLongPhraseID = cur.fetchall()

        # Get list of long phrase IDs in context semantic field table
        # GUY: added DISTINCT
        cur = con.cursor()
        cur.execute(""" SELECT DISTINCT "phrase_id" FROM "context_phrase" ;""" )
        csfPhraseID = cur.fetchall()
        csfLongPhraseID = set(csfPhraseID).intersection(allLongPhraseID)
        print("long phrase size: %s" % (len(csfLongPhraseID)))
        # Create dictionary {longPhraseID: phraseText}
        longPhraseText = dict()
        counter=0
        for lpid in csfLongPhraseID:
            counter+=1
            
            phraseID = lpid[0]
            #phrase = self.phrases[phraseID]
            #if phrase.getFlag()==0:
            cur.execute(""" SELECT "phrase_text" FROM phrase WHERE "phrase_id"=%s;""",([phraseID]) )
            phraseText = cur.fetchall()
            #longPhraseText.update({phraseID:phrase.getText()})
            longPhraseText.update({phraseID:phraseText[0][0]})
            if counter % 1000 == 0:
                print(counter)
                #print(phraseText)
                print(phraseText[0][0])

        # Update shared word table
        from nltk import word_tokenize
        
        """
        GUY: It seems postgresql consider {key2:key1} a violation of {key1:key2}
        We will therefore prevent permutations and go with combinations
        Another issue is that we would violate primary constraints when two words share multiple words.
        Hence, Primary key should consist of 3 columns to be unique: "longPhraseID, siblingID, sharedWord"
        """
        donotpermute=[]
        counter=0
        for lp1 in longPhraseText.keys():
            counter+=1
            if counter % 1000 ==0:
                print("counter: %s" % counter)
            tokens_1 = word_tokenize(longPhraseText[lp1])
            tokens_1b=list(set(tokens_1))
            donotpermute.append(lp1)
            #print("list of phrase ID not to permute")
            #print(donotpermute)
            counter2=0
            for lp2 in longPhraseText.keys():
                counter2+=1
                if lp2 not in donotpermute:
                    tokens_2 = word_tokenize(longPhraseText[lp2])
                    tokens_2b=list(set(tokens_2))
                    for token in tokens_1b:
                        if token in tokens_2b:
                            longPhraseID = lp1
                            siblingID = lp2
                            sharedWord = token
                            swpilp = tokens_1.index(token)
                            swpis = tokens_2.index(token)
                            cur = con.cursor()
                            cur.execute("""INSERT INTO "shared_word" ("long_phrase_id", "sibling_id", "shared_word", "shared_word_position_in_long_phrase", "shared_word_position_in_sibling")
                            VALUES (%s,%s,%s,%s,%s)""", ([longPhraseID, siblingID, sharedWord, swpilp, swpis]))  
                            if counter2 % 1000==0:
                                print("counter 1: %s, tokens_1: %s, tokens_2: %s, shared word:%s, pos 1: %s, pos 2: %s" %(counter,tokens_1,tokens_2,sharedWord,swpilp,swpis))
                            
    def updateContextSpellingSimilarity(self):
        
        # Define Levenshtein distance
        def levenshtein(s, t):
            """ 
                Returns the Levenshtein distance between the strings s and t.
                Source: https://www.python-course.eu/levenshtein_distance.php
            """
            rows = len(s)+1
            cols = len(t)+1
            dist = [[0 for x in range(cols)] for x in range(rows)]
            for i in range(1, rows):
                dist[i][0] = i
            for i in range(1, cols):
                dist[0][i] = i
            for col in range(1, cols):
                for row in range(1, rows):
                    if s[row-1] == t[col-1]:
                        cost = 0
                    else:
                        cost = 1
                    dist[row][col] = min(dist[row-1][col] + 1,      # deletion
                                         dist[row][col-1] + 1,      # insertion
                                         dist[row-1][col-1] + cost) # substitution
    
            return dist[row][col]
        
        # Delete all existing entries in context spelling similarity table
        cur = con.cursor()
        cur.execute("""DELETE FROM "context_spelling_similarity";""")
        
        # Create dictionary {contextID: contextName}
        """
        contextName = dict()
        for contextID in self.contexts.keys():
            context=self.contexts[contextID]
            contextName.update({contextID:context.getName()})     
        """ 
            
        cur.execute(""" SELECT "context_id" FROM context;""" )
        contextIDs = cur.fetchall()
        
        # Update context spelling similarity table
        for contextID_1 in contextIDs:
            cur.execute(""" SELECT "context_name" FROM context WHERE "context_id"=%s;""",(contextID_1))
            contextName_1 = cur.fetchall()
            for contextID_2 in contextIDs:
                if contextID_1[0] != contextID_2[0]:
                    cur.execute(""" SELECT "context_name" FROM context WHERE "context_id"=%s;""",(contextID_2))
                    contextName_2 = cur.fetchall()
                    similarityIndex = levenshtein(contextName_1[0][0].lower(), contextName_2[0][0].lower())
                    if similarityIndex <= 3:
                        cur = con.cursor()
                        cur.execute("""INSERT INTO "context_spelling_similarity" ("context_id", "similar_spelling_context_id", "similarity_index")
                        VALUES (%s,%s,%s)""", ([contextID_1[0], contextID_2[0], similarityIndex]))
                        print("context ID1 %s, %s, context IDs2 %s, %s, similarity index %s" %(contextID_1[0], contextName_1[0][0], contextID_2[0], contextName_2[0][0], similarityIndex))
                          
    def updatePhraseSpellingSimilarity(self):
        
        # Define Levenshtein distance
        def levenshtein(s, t):
            """ 
                Returns the Levenshtein distance between the strings s and t.
                Source: https://www.python-course.eu/levenshtein_distance.php
            """
            rows = len(s)+1
            cols = len(t)+1
            dist = [[0 for x in range(cols)] for x in range(rows)]
            for i in range(1, rows):
                dist[i][0] = i
            for i in range(1, cols):
                dist[0][i] = i
            for col in range(1, cols):
                for row in range(1, rows):
                    if s[row-1] == t[col-1]:
                        cost = 0
                    else:
                        cost = 1
                    dist[row][col] = min(dist[row-1][col] + 1,      # deletion
                                         dist[row][col-1] + 1,      # insertion
                                         dist[row-1][col-1] + cost) # substitution
    
            return dist[row][col] 
        
        # Delete all existing entries in phrase spelling similarity table
        cur = con.cursor()
        cur.execute("""DELETE FROM "phrase_spelling_similarity";""")

        # Create dictionary {phraseID: phraseText}
        phraseText = dict()
        
        """
        Revision from Guy. We do not need to apply the methods to all phrases of the universe
        but only to those phrases found into the context semantic field table
        """
        cur = con.cursor()
        cur.execute("""SELECT DISTINCT "context_phrase"."phrase_id" FROM phrase,"context_phrase" WHERE "red_flag"=0 AND phrase."phrase_id"="context_phrase"."phrase_id";""" )
        csfPhraseID = cur.fetchall()
        
        for phraseID in csfPhraseID:
            cur.execute(""" SELECT "phrase_text" FROM phrase WHERE "phrase_id"=%s;""",([phraseID[0]]) )
            text = cur.fetchall()
            if text:
                phraseText.update({phraseID:text[0][0]})
        
        """
        for phraseID in self.phrases.keys():
            phrase=self.phrases[phraseID]
            phraseText.update({phraseID:phrase.getText()})
        """
        
        # Update phrase spelling similarity table    
        counter=0
        print("phrasetext size: %s" % len(phraseText))
        for phraseID_1 in phraseText.keys():
            counter+=1
            if counter % 1000 ==0:
                print("counter: %s" % counter)
            phraseText_1 = phraseText[phraseID_1]
            counter2=0
            for phraseID_2 in phraseText.keys():
                counter2+=1
                if phraseID_1 != phraseID_2:
                    phraseText_2 = phraseText[phraseID_2]
                    similarityIndex = levenshtein(phraseText_1, phraseText_2)
                    if similarityIndex <= 3:
                        cur = con.cursor()
                        cur.execute("""INSERT INTO "phrase_spelling_similarity" ("phrase_id", "similar_spelling_phrase_id", "similarity_index")
                        VALUES (%s,%s,%s)""", ([phraseID_1, phraseID_2, similarityIndex]))
                        if counter2 % 1000==0:
                                print("counter 1: %s, phrase 1: %s, phrase 2: %s, similarity index %s" %(counter,phraseText[phraseID_1],phraseText[phraseID_2],similarityIndex))
   
    
    """
    NEW NEW NEW NEW NEW NEW
    SPECIAL METHODS JUST FOR THE WORD MAZE GAME
    """
              
    def updateFrequencyDistanceTable(self):   

        # Delete all existing entries in frequency distance table
        cur = con.cursor()
        cur.execute("""DELETE FROM "phrase_frequency_and_distance";""")

        cur.execute(""" SELECT DISTINCT "phrase_id" FROM "context_phrase";""" )
        phraseIDs = cur.fetchall()

        cur.execute(""" SELECT "context_id" FROM context;""" )
        contextIDs = cur.fetchall()

        counter=0

        for phraseID in phraseIDs:
            
            phraseID=phraseID[0]
            
            phrase=self.phrases[phraseID]
            
            if counter % 500 == 0:
                print(counter)
                print(phrase.getText())
            counter+=1
            for contextID in contextIDs:
                contextID=contextID[0]
                context=self.contexts[contextID]
                cur.execute(""" SELECT "phrase_distance_to_context" FROM "phrase_distance_to_context" WHERE "phrase_id"=%s AND "context_id"=%s;""",([phraseID,contextID]))
                distance = cur.fetchall()[0][0]
                
                phraseCountInContext=phrase.getPhraseCountPerContext(contextID)
                totalPhraseCount=self.contextVolumeByPhraseLength[(contextID,phrase.getPhraseLength())]
                
                if totalPhraseCount==0:
                    phraserelativefrequency=0
                else:
                    phraserelativefrequency=phraseCountInContext/totalPhraseCount
               
                if totalPhraseCount>0 and phraserelativefrequency>0:
                    cur.execute("""INSERT INTO "phrase_frequency_and_distance" ("phrase_id", "context_id", "phrase_relative_frequency","phrase_distance_to_context")
                    VALUES (%s,%s,%s,%s)""", ([phraseID, contextID,phraseCountInContext/totalPhraseCount,distance]))
                
                print("contextID")
                print(contextID)
                cur.execute(""" SELECT "phrase_relative_frequency" FROM "phrase_frequency_and_distance" WHERE "phrase_id" = %s AND "context_id"=%s; """, ([phraseID,contextID]))
                frequency = cur.fetchall()
                if frequency:
                    frequency =frequency[0][0]
                    cur.execute(""" UPDATE "phrase_frequency_and_distance" SET "phrase_difficulty" = %s WHERE "phrase_id" = %s AND "context_id"=%s; """, ([self.phraseDifficulty(frequency),phraseID,contextID]))

    def phraseDifficulty(self, frequency):
        
        index = frequency * 100000

        if index >= 40:
            return 1
        elif index >= 20:
            return 2
        elif index >= 1:
            return 3
        else:
            return 4
            

class Context(object):

    def __init__(self, contextName, contextID, ancestorsID, independent, ICIndex, RCIndex, dimension, phraseCount):
        """
        NOTE:
            A context is defined by an ID, a list of ancestors, an independence status,
            an index if the context is independent, and a dimension. The dimension is the dimension
            of the phrase vector space. It is the count of all independent contexts.
        """
        
        self.contextName=contextName
        self.contextID = contextID
        self.ancestorsID=ancestorsID
        self.independent=independent
        self.independentDescendantsID=[]
        self.ICIndex=ICIndex
        self.RCIndex=RCIndex
        self.dimension=dimension
        self.contextAxis = []
        self.phraseCount=phraseCount
        self.lexicalSetBoundary=0
        self.lexicalSet=dict()

        """
        NOTE:
            A context is an axis in the phrase vector space. That axis has a basis
            which is a list of coordinates across the independent contexts.
            An example of basis is (1,0,0,0,1,0,0,0,0,0). It means that the context
            is generated by context 1 and context 5.
            Another example of basis is (1,0,1,0,0,0,0,0,0,1). It means that the context
            is generated by context 1, context 3 and context 10.
            Initially, we create a basis (0,0,0,0,0,0,0,........). This basis will be updated
            at a later stage using the method updateBasis()
        """
        
        self.initializeAxis()
    
    def isIndependent(self):
        return self.independent
    
    def getID(self):
        return self.contextID

    def initializeAxis(self):
        self.contextAxis=[0]*self.dimension
    
    def updateAxis(self,ICIndex,ancestors):
        
        if self.contextAxis[ICIndex]==0:
            self.contextAxis[ICIndex]=1
        for ancestor in ancestors:
            ancestor.updateAncestorAxis(self.ICIndex)
            
    def updateAncestorAxis (self,ICIndex):
        if self.contextAxis[ICIndex]==0:
            self.contextAxis[ICIndex]=1
    
    def addIndependentDescendantsID(self, descendantID):
        self.independentDescendantsID.append(descendantID)
        
    def getIndependentDescendantsID(self):
        return self.independentDescendantsID
        
    def getName(self):
        return self.contextName
    
    def getAxis(self):
        return self.contextAxis
    
    def getICIndex(self):
        return self.ICIndex
    
    def getRCIndex(self):
        return self.RCIndex
    
    def getAncestorsID(self):
        return self.ancestorsID  

    def getPhraseCount(self):
        
        return self.phraseCount
    
    def setLexicalSetBoundary(self, boundary):
     
        self.lexicalSetBoundary=boundary
        
    def getLexicalSetBoundary(self):
        
        return self.lexicalSetBoundary
    
    def setLexicalSet(self, lexicalSet):
        self.lexicalSet = lexicalSet
        
    def updateLexicalSet(self, phrase, distance):
        self.lexicalSet.update({phrase: distance})
        
    def getLexicalSet(self):
    
        return self.lexicalSet

    def updateAncestorPhraseCount(self, phraseCount, ancestors):
        
        for ancestor in ancestors:
            ancestor.incrementPhraseCount(phraseCount)
            
    def incrementPhraseCount(self, incrementalCount):
        
        for phraseLength in self.phraseCount.keys():
            """
            phrase length is the second element of the key which is a tupe (contextID,length)
            """
            phraseLength=phraseLength[1]
            self.phraseCount[(self.contextID,phraseLength)] += incrementalCount[(self.contextID,phraseLength)]
            
    def __str__(self):    
        
        return "I am the Context class"

"""
The class Phrase defines a phrase.
"""


class Phrase(object):

    def __init__(self, phraseText, phraseID, phraseLength, index, phraseCountPerContext, documentPerContext, contexts):
        
        """
        NOTE:
            A phrase is defined by an ID and an index which is its position
            in the self.phrases dictionary
        """
        self.phraseText = phraseText
        self.phraseID = phraseID
        self.phraseLength = phraseLength
        self.index = index
        self.phraseCountPerContext = phraseCountPerContext
        self.phraseCrossPresenceOverContextChildren = dict()
        self.documentPerContext = documentPerContext
        self.lexicalSetBoundary = 0
        self.lexicalSetByContext = None
        self.contexts = contexts
        
        self.redFlag = 0
        self.assignFlag()

        self.updatePresenceOverContextChildren()
    
    def assignFlag(self):
        """
        NOTE:
            This class identifies any sequence of 1 to more words as a "phrase".
            Assuming that a "phrase" is any sequence of 1 to multiple words is incorrect.
            A phrase is a sequence of two or more words arranged in a grammatical construction and acting
            as a unit in a sentence.
            For example: "of two or" is not a phrase. "grammatical construction" is a phrase and represents
            a particular type of construction.
            The class Phrase does not make a distinction between sequence of words that play as a unit and other
            sequence of words.
            
            A "sequence of words" will receive a red flag (redflag=1) if it is not a standalone unit.
            
            Valid sequence of words would be those that represents nouns, verbs, adjective and adverbs.
            We are not interested in all other parts of speech (prepositions, articles, pronouns, etc...)
            and will red flag them. Note that a phrase such as "United States of America" represents a country and
            is therefore considered a noun. Phrasal verbs (beat off, blast off, blow out, etc....) are considered verbs.
            
            The following part of speech will be red flagged when seen at the beginning or the end of a sequence of words:
            - Articles: the, a, an
            - Pronouns: I, me, we, us, you, he, him, she, her, it, they, them, my, your, his, her, its, us, our, your,
            their, myself, himself, herself, itself, ourselves, yourselves, themselves, this, these, that, those, former,
            latter, who, whom, which, when, where, what, which, whose, why, how, something, anything, nothing, somewhere,
            anywhere, nowhere, someone, anyone, no one, our, ours, this, some, none, no, thou, thee, ye
            - Prepositions: aboard, about, above, absent, across, after, against, gainst, again, along, alongst, alongside,
            amid, amidst, midst, among, amongst, apropos, apud, around, as, astride, at, atop, ontop, before, afore, tofore,
            behind, ahind, below, ablow, beneath, beside, besides, between, atween, beyond, ayond, but, by, chez, circa, 
            despite, spite, down, during, except, for, from, in, inside, into, less, like, minus, near, nearer, nearest,
            anear, notwithstanding, of, off, on, onto, opposite, out, outen, outside, over, per, plus, since, than, through,
            thru, throughout, thruout, till, to, toward, towards, under, underneath, unlike, until, unto, up, upon,
            upside, versus, via, vis-à-vis, with, within, without, worth, abaft, abeam, aboon, abun, abune, afront, ajax,
            alongst, aloof, anenst, anent, athwart, atop, ontop, behither, betwixt, atwix, bewest, benorth, emforth,
            forby, foreanent, forenenst, foregain, foregainst, forth, fromward, froward, fromwards, furth, gainward,
            imell, inmid, inmiddes, mauger, maugre, nearhand, next, outwith, overthwart, quoad, umbe, umb,
            unto, uptill
            - Postpositions: ago, apart, aside, aslant (archaic), away, hence, through, withal
            - Conjunctions: for, and, nor, but, or, yet, so, either, both, whether, rather, because, if, while
            - Select verbs: be, is, isn't,are,ain't, was, wasn't, were, weren't, am, will, shall, won't, should, shouldn't, could, couldn't, would,
            wouldn't, has, have, had, do, don't, did,didn't
            
            - Select 1 letter words: a, b, c, d, e, f, g, h, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z
            - Other words: not, other, too, much, then,another, been, being, having, thus, more, most, also, many, few, fewer, fewest
            - Numbers: 1, 2, 3, 4, 5, 6, 7, 8, 9, 0
        """
        
        """
        TASK 4:
            4- Check "self.phraseText". If it starts (first word) or ends (last word) with any of the above
            listed articles, pronouns, prepositions, postpositions, conjunctions, select verbs, then
            set attribute self.redFlag to 1.          
        """
        
        ######### revised 06/04/2018
        from nltk.tokenize import RegexpTokenizer
        
        tokenizer = RegexpTokenizer(r'[a-zA-Z0-9_]*[\']{0,1}[a-zA-Z0-9_]+')
        flagWordsString = "the, a, an, I, me, we, us, you, he, him, she, her, it, they, them, my, your, his, her, its, us, our, your, their, myself, himself, herself, itself, ourselves, yourselves, themselves, this, these, that, those, former, latter, who, whom, which, when, where, what, which, whose, why, how, something, anything, nothing, somewhere, anywhere, nowhere, someone, anyone, no one, our, ours, this, some, none, no, thou, thee, ye, aboard, about, above, absent, across, after, against, gainst, again, along, alongst, alongside, amid, amidst, midst, among, amongst, apropos, apud, around, as, astride, at, atop, ontop, before, afore, tofore, behind, ahind, below, ablow, beneath, beside, besides, between, atween, beyond, ayond, but, by, chez, circa, despite, spite, down, during, except, for, from, in, inside, into, less, like, minus, near, nearer, nearest, anear, notwithstanding, of, off, on, onto, opposite, out, outen, outside, over, per, plus, since, than, through,thru, throughout, thruout, till, to, toward, towards, under, underneath, unlike, until, unto, up, upon, upside, versus, via, vis-à-vis, with, within, without, worth, abaft, abeam, aboon, abun, abune, afront, ajax, alongst, aloof, anenst, anent, athwart, atop, ontop, behither, betwixt, atwix, bewest, benorth, emforth, forby, foreanent, forenenst, foregain, foregainst, forth, fromward, froward, fromwards, furth, gainward, imell, inmid, inmiddes, mauger, maugre, nearhand, next, outwith, overthwart, quoad, umbe, umb, unto, uptill, ago, apart, aside, aslant, away, hence, through, withal, for, and, nor, but, or, yet, so, either, both, whether, rather, because, if, while, be, is, isn't,are,ain't, was, wasn't, were, weren't, am, will, shall, won't, should, shouldn't, could, couldn't, would, wouldn't, has, have, had, do, don't, did,didn't, a, b, c, d, e, f, g, h, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z"
        flagWords = tokenizer.tokenize(flagWordsString) 
        tokenizedPhraseText = tokenizer.tokenize(self.phraseText)
        
        if (tokenizedPhraseText[0] in flagWords) | (tokenizedPhraseText[-1] in flagWords):
            self.redFlag = 1
            #print(tokenizedPhraseText)
        else:
            self.redFlag = 0
            #print(tokenizedPhraseText)
        
        #return self.redFlag
        #########
        
    def getFlag(self):
        return self.redFlag
    
    def getPhraseID(self):
        
        return self.phraseID
    
    def getPhraseLength(self):
        
        return self.phraseLength
    
    def getIndex(self):
        
        return self.index
    
    def getText(self):
        
        return self.phraseText
    
    def getPhraseCountPerContext(self,contextID):
        
        return self.phraseCountPerContext[(contextID,self.phraseID)]
    
    def getDocumentPerContext(self):
        
        return self.documentPerContext
    
    def setLexicalSetBoundary(self,boundary): 
     
        self.lexicalSetBoundary=boundary
        
    def getLexicalSetBoundary(self):
        
        return self.lexicalSetBoundary

    def initializeLexicalSetByContext(self,contextCount):
        self.lexicalSetByContext=[dict()]*contextCount
    
    def updateLexicalSetByContext(self,lexicalSet,contextRCIndex):
        
        self.lexicalSetByContext[contextRCIndex]=lexicalSet
        
    def getLexicalSetByContext(self):
    
        return self.lexicalSetByContext

    def updatePresenceOverContextChildren(self):
        
        significanceThreshold=0.5

        for contextID in self.phraseCountPerContext.keys():
            """
            keys in phraseCountPerContext are tuples (contextID,phraseID)
            we need first value of the tuple
            """
            contextID=contextID[0]
            context=self.contexts[contextID]
            presenceCount=0
            if self.getPhraseCountPerContext(contextID)==0:
                self.phraseCrossPresenceOverContextChildren.update({contextID:0})
            else:
                if context.isIndependent():
                    self.phraseCrossPresenceOverContextChildren.update({contextID:1})
                else:
                    for descendantID in context.getIndependentDescendantsID():
                        if self.getPhraseCountPerContext(descendantID)>0:
                            presenceCount+=1
                    if presenceCount/len(context.getIndependentDescendantsID())>significanceThreshold:
                        self.phraseCrossPresenceOverContextChildren.update({contextID:1})
                    else:
                        self.phraseCrossPresenceOverContextChildren.update({contextID:0})

    def getPhraseCrossPresenceOverContextChildren(self):

        return self.phraseCrossPresenceOverContextChildren      

    def isSignificantlyPresentInContext(self,contextID):
        
        if self.phraseCrossPresenceOverContextChildren[contextID]==0:
            return False
        return True

    def __str__(self):    
        
        return "I am the Phrase class"
