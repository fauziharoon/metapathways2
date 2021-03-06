#!/usr/bin/python
# File created on Nov 27 Jan 2012
from __future__ import division

__author__ = "Kishori M Konwar"
__copyright__ = "Copyright 2013, MetaPathways"
__credits__ = ["r"]
__version__ = "1.0"
__maintainer__ = "Kishori M Konwar"
__status__ = "Release"

try:
     from os import makedirs, sys, remove, path
     import re
     from optparse import OptionParser, OptionGroup

     from python_modules.LCAComputation import *
     from python_modules.MeganTree import *
     from python_modules.metapaths_utils  import parse_command_line_parameters, fprintf, printf
     from python_modules.sysutil import getstatusoutput
except:
     print """ Could not load some user defined  module functions"""
     print """ Make sure your typed \"source MetaPathwaysrc\""""
     print """ """
     sys.exit(3)


usage= """./MetapathWays_annotate.py -d dbname1 -b parsed_blastout_for_database1 [-d dbname2 -b parsed_blastout_for_database2 ] --input-annotated-gff input.gff  """
parser=None
def createParser():
     global parser
     parser = OptionParser(usage)
     parser.add_option("-b", "--blastoutput", dest="input_blastout", action='append', default=[],
                       help='blastout files in TSV format [at least 1 REQUIRED]')
     
     parser.add_option("-d", "--dbasename", dest="database_name", action='append', default=[],
                       help='the database names [at least 1 REQUIRED]')
     
     cutoffs_group =  OptionGroup(parser, 'Cuttoff Related Options')
     
     cutoffs_group.add_option("--min_score", dest="min_score", type='float', default=20,
                       help='the minimum bit score cutoff [default = 20 ] ')
     
     cutoffs_group.add_option("--max_evalue", dest="max_evalue", type='float', default=1e-6,
                       help='the maximum E-value cutoff [ default = 1e-6 ] ')
     cutoffs_group.add_option("--min_length", dest="min_length", type='float', default=30,
                       help='the minimum length of query cutoff [default = 30 ] ')
     cutoffs_group.add_option("--max_length", dest="max_length", type='float', default=10000,
                       help='the maximum length of query cutoff [default = 10000 ] ')
     
     
     cutoffs_group.add_option("--min_identity", dest="min_identity", type='float', default=20,
                       help='the minimum identity of query cutoff [default 30 ] ')
     cutoffs_group.add_option("--max_identity", dest="max_identity", type='float', default=100,
                       help='the maximum identity of query cutoff [default = 100 ] ')
     
     cutoffs_group.add_option("--limit", dest="limit", type='float', default=5,
                       help='max number of hits per query cutoff [default = 5 ] ')
     
     cutoffs_group.add_option("--min_bsr", dest="min_bsr", type='float', default=0.0,
                       help='minimum BIT SCORE RATIO [default = 0.30 ] ')
     parser.add_option_group(cutoffs_group)
     
     
     output_options_group =  OptionGroup(parser, 'Output table Options')
     output_options_group.add_option("--ncbi-taxonomy-map", dest="ncbi_taxonomy_map",  default=False,
                       help='add the ncbi taxonomy map ')
     
     output_options_group.add_option( "--input-cog-maps", dest="input_cog_maps",
                      help='input cog maps file')
     
     output_options_group.add_option( "--subsystems2peg-file", dest="subsystems2peg_file", default = False,
                      help='the subsystems to peg file from fpt.theseed.org')
     
     output_options_group.add_option( "--input-kegg-maps", dest="input_kegg_maps",
                      help='input kegg maps file')
     
     output_options_group.add_option( "--input-seed-maps", dest="input_seed_maps",
                      help='input seed maps file')
     
     output_options_group.add_option('--input-annotated-gff', dest='input_annotated_gff',
                     metavar='INPUT', help='Annotated gff file [REQUIRED]')
     
     output_options_group.add_option('--output-dir', dest='output_dir',
                     metavar='INPUT', help='Output directory [REQUIRED]')
     parser.add_option_group(output_options_group)
     
     lca_options_group =  OptionGroup(parser, 'LCA algorithm Options')
     lca_options_group.add_option("--lca-min-score", dest="lca_min_score",  type='float', default=50,
                       help='minimum BLAST/LAST score to consider as for LCA rule')
     lca_options_group.add_option("--lca-top-percent", dest="lca_top_percent",  type='float', default=10,
                       help='set of considered matches are within this percent of the highest score hit')
     lca_options_group.add_option("--lca-min-support", dest="lca_min_support",  type='int', default=5,
                       help='minimum number of reads that must be assigned to a taxon for ' +\
                            'that taxon to be present otherwise move up the tree until there ' + 
                            'is a taxon that meets the requirement')
     parser.add_option_group(lca_options_group)


def check_arguments(opts, args):
    if len(opts.input_blastout) == 0:
         print "There sould be at least one blastoutput file"  
         return False

    if len(opts.database_name) == 0:
         print "There sould be at least one database name"  
         return False

    if len(opts.input_blastout) != len(opts.database_name)  :
         print "The number of database names, blastoutputs files should be equal"
         return False

    if opts.input_annotated_gff == None:
       print "Must specify the input annotated gff file"
       return False

    if opts.output_dir == None:
       print "Must specify the output dir"
       return False

    return True

def insert_attribute(attributes, attribStr):
     rawfields = re.split('=', attribStr)
     if len(rawfields) == 2:
       attributes[rawfields[0].strip().lower()] = rawfields[1].strip()

def split_attributes(str, attributes):
     rawattributes = re.split(';', str)
     for attribStr in rawattributes:
        insert_attribute(attributes, attribStr)

     return attributes

def insert_orf_into_dict(line, contig_dict):
     rawfields = re.split('\t', line)
     fields = []
     for field in rawfields:
        fields.append(field.strip());
    
     
     if( len(fields) != 9):
       return

     attributes = {}
     attributes['seqname'] =  fields[0]   # this is a bit of a  duplication  
     attributes['source'] =  fields[1]
     attributes['feature'] =  fields[2]
     attributes['start'] =  int(fields[3])
     attributes['end'] =  int(fields[4])

     try:
        attributes['score'] =  float(fields[5])
     except:
        attributes['score'] =  fields[5]

     attributes['strand'] =  fields[6]
     attributes['frame'] =  fields[7]
     
     split_attributes(fields[8], attributes)

     if not fields[0] in contig_dict :
       contig_dict[fields[0]] = []

     contig_dict[fields[0]].append(attributes)
  

class GffFileParser(object):

   def __init__(self, gff_filename):
        self.Size = 10000
        self.i=0
        self.orf_dictionary = {}
        self.gff_beg_pattern = re.compile("#")
        self.lines= []
        self.size=0
        try:
           self.gff_file = open( gff_filename,'r')
        except AttributeError:
           print "Cannot read the map file for database :" + dbname
           sys.exit(0)

   def __iter__(self):
        return self

   def refillBuffer(self):
       self.orf_dictionary = {}
       line = self.gff_file.readline()
       i = 0
       while line and i < self.Size:
          line=self.gff_file.readline()
          if self.gff_beg_pattern.search(line):
            continue
          if not line:
            break
          insert_orf_into_dict(line, self.orf_dictionary)
          i += 1

       self.orfs = self.orf_dictionary.keys()
       self.size = len(self.orfs)
       self.i = 0

   def next(self):
        if self.i == self.size:
           self.refillBuffer()

        if self.size==0:
           self.gff_file.close()
           raise StopIteration()

        #print self.i
        if self.i < self.size:
           self.i = self.i + 1
           return self.orfs[self.i-1]


def process_gff_file(gff_file_name, orf_dictionary):
     try:
        gfffile = open(gff_file_name, 'r')
     except IOError:
        print "Cannot read file " + gff_file_name + " !"

     gff_lines = gfffile.readlines()
     gff_beg_pattern = re.compile("^#")
     gfffile.close()
     
     for line in gff_lines:
        line = line.strip() 
        if gff_beg_pattern.search(line):
          continue
        insert_orf_into_dict(line, orf_dictionary)


def create_dictionary(databasemapfile, annot_map):
       seq_beg_pattern = re.compile(">")

       dbmapfile = open( databasemapfile,'r')
       lines=dbmapfile.readlines()
       dbmapfile.close()
       for line in lines:
          if seq_beg_pattern.search(line):
              words = line.rstrip().split()
              name = words[0].replace('>','',1)
               
              words.pop(0)
              annotation = ' '.join(words)
              annot_map[name]= annotation
           

def copyList(a, b):
    [ b.append(x) for x in a ]

    
def get_species(hit):
    if not 'product' in hit: 
        return None

    species = []
    try:
        m = re.findall(r'\[([^\[]+)\]', hit['product'])
        if m != None:
          copyList(m,species)
    except:
          return None

    if species:
       return species
    else:
       return None


def create_annotation(results_dictionary, annotated_gff,  output_dir, ncbi_taxonomy_tree_file, min_score, top_percent, min_support):
    meganTree = None
    lca = None
    if 'refseq' in results_dictionary:
        lca = LCAComputation(ncbi_taxonomy_tree_file)
        lca.setParameters(min_score, top_percent, min_support)
        meganTree = MeganTree(lca)

    if not path.exists(output_dir):
       makedirs(output_dir)

   
    orf_dictionary={}
    #process_gff_file(annotated_gff, orf_dictionary)
    gffreader = GffFileParser(annotated_gff)
    output_table_file = open(output_dir + '/functional_and_taxonomic_table.txt', 'w')
    fprintf(output_table_file, "ORF_ID\tORF_length\tstart\tend\tContig_Name\tContig_length\tstrand\tec\ttaxonomy\tproduct\n")

    count = 0
    for contig in  gffreader:
       for orf in  gffreader.orf_dictionary[contig]:
          taxonomy = None
          if count%10000==0 :
             pass 
          species = []
          if 'refseq' in results_dictionary:
            if orf['id'] in results_dictionary['refseq']:
                for hit in results_dictionary['refseq'][orf['id']]:
                   if hit['bitscore'] >= min_score:
                      names = get_species(hit)
                      if names:
                        species.append(names) 
                      #print '---------------------------'
          #         else:
          #              print "hit " + hit['query']  + ' ' + hit['dbname'] + ' ' + str(hit['bitscore'] )
          if lca: 
            taxonomy=lca.getTaxonomy(species)
          fprintf(output_table_file, "%s", orf['id'])
          fprintf(output_table_file, "\t%s", orf['orf_length'])
          fprintf(output_table_file, "\t%s", orf['start'])
          fprintf(output_table_file, "\t%s", orf['end'])
          fprintf(output_table_file, "\t%s", orf['seqname'])
          fprintf(output_table_file, "\t%s", orf['contig_length'])
          fprintf(output_table_file, "\t%s", orf['strand'])
          fprintf(output_table_file, "\t%s", orf['ec'])
          # fprintf(output_table_file, "\t%s", str(species))
          fprintf(output_table_file, "\t%s", taxonomy)
          fprintf(output_table_file, "\t%s\n", orf['product'])
          if meganTree and taxonomy != '':
              meganTree.insertTaxon(taxonomy)
              # print 'inserted taxon of taxonomy : ', taxonomy
          #print meganTree.getChildToParentMap()
    output_table_file.close()
    # print meganTree.getParentToChildrenMap()

    if meganTree:
        print output_dir + '/megan_tree.tre'
        megan_tree_file = open(output_dir + '/megan_tree.tre', 'w')
        #print meganTree.printTree('1')
        # exit()
        fprintf(megan_tree_file,  "%s;", meganTree.printTree('1'))
        # print 'wrote out megan_tree_file'
        megan_tree_file.close()
    


            #write_annotation_for_orf(outputgff_file, candidatedbname, dbname_weight, results_dictionary, orf_dictionary, contig, candidate_orf_pos,  orf['id']) 


def process_product(product, database, similarity_threshold=0.9):
    """Returns the best set of products from the list of (*database*,
    *product*) tuples *products*.

    Each product in the set is first trimmed down, removing database-specific
    information.

    The set is then determined by first sorting the products by length
    (ascending), and then, for each product, sequentially applying the longest
    common substring algorithm to determine the similarity between the product
    and already determined products. If this similarity is greater than the
    specified *similarity_threshold*, the longer of the two products is chosen
    to be a determined product.
    """

    processed_product = ''

    # COG
    if database == 'cog':
        results = re.search(r'Function: (.+?) #', product)
        if results:
           processed_product=results.group(1)

    # KEGG: split and process

    elif database == 'kegg':
        kegg_products = re.split(r'\s*;\s+', product)
        for kegg_product in kegg_products:
            # Toss out organism:ID pairs, gene names, and KO IDs
            kegg_product = re.sub(r'^lcl[|]', '', kegg_product)
            kegg_product = re.sub(r'[a-z]{3}:\S+', '', kegg_product)
            kegg_product = kegg_product.strip()
            kegg_product = re.sub(r'(, \b[a-z]{3}[A-Z]?\b)+', '', kegg_product)
            kegg_product = re.sub(r'^\b[a-z]{3}[A-Z]?\b', '', kegg_product)
            kegg_product = re.sub(r'\bK\d{5}\b', '', kegg_product)
            
            # Also toss out anything between square brackets

            kegg_product = re.sub(r'\[.+?\]', '', kegg_product)

            if kegg_product.strip():
                processed_product=kegg_product.strip()
                

    # RefSeq: split and process

    elif database == 'refseq':
        for subproduct in product.split('; '):
            subproduct = re.sub(r'[a-z]{2,}\|(.+?)\|\S*', '', subproduct)
            subproduct = re.sub(r'\[.+?\]', '', subproduct)
            if subproduct.strip():
                processed_product=subproduct.strip()

    # MetaCyc: split and process

    elif database == 'metacyc':
        
        # Pull out first name after the accession code:

        product_name = product.split('#')[0].strip()
        product_name = re.sub(r'^[^ ]* ', '', product_name)
        product_name = re.sub(r' OS=.*', '', product_name)
        if product_name:
            processed_product=product_name
    # Generic
    else:
        processed_product=product

    words = [ x.strip() for x in processed_product.split() ]
    filtered_words =[]
    underscore_pattern = re.compile("_")
    arrow_pattern = re.compile(">")
    for word in words:
       if not  underscore_pattern.search(word) and not arrow_pattern.search(word):
           filtered_words.append(word)
    
    #processed_product = ' '.join(filtered_words)
    # Chop out hypotheticals
    processed_product = remove_repeats(filtered_words)
    processed_product = re.sub(';','',processed_product)



    processed_product = re.sub(r'hypothetical protein','', processed_product)

    return processed_product

def remove_repeats(filtered_words):
    word_dict = {}
    newlist = []
    for word in filtered_words:
       if not word in word_dict:
          if not word in ['', 'is', 'have', 'has', 'will', 'can', 'should',  'in', 'at', 'upon', 'the', 'a', 'an', 'on', 'for', 'of', 'by', 'with' ,'and',  '>' ]:
             word_dict[word]=1
             newlist.append(word)
    return ' '.join(newlist)


class BlastOutputTsvParser(object):

    def __init__(self, dbname,  blastoutput):
        self.dbname = dbname
        self.blastoutput = blastoutput
        self.i=0
        self.SIZE = 10000
        self.data = {}
        self.fieldmap={}
        self.seq_beg_pattern = re.compile("#")
        self.lines = []

        try:
           self.blastoutputfile = open( blastoutput,'r')
           line = self.blastoutputfile.readline()
           if not self.seq_beg_pattern.search(line) :
              print "First line must have field header names and begin with \"#\""
              sys.exit(0)
           header = re.sub('#','',line)

           fields = [ x.strip()  for x in header.rstrip().split('\t')]
           k = 0 
           for x in fields:
            self.fieldmap[x] = k 
            k+=1

        except AttributeError:
           print "Cannot read the map file for database :" + dbname
           sys.exit(0)

    def refillBuffer(self):
       i = 0 
       self.lines = []
       line = self.blastoutputfile.readline()
       while line and i < self.SIZE:
         line=self.blastoutputfile.readline()
         if not line:
           break
         self.lines.append(line)
         i += 1

       self.size = len(self.lines)
 
  
    def __iter__(self):
        return self
 
    def next(self):
        if self.i % self.SIZE == 0:
           self.refillBuffer()

        if self.i % self.SIZE < self.size:
           fields = [ x.strip()  for x in self.lines[self.i % self.SIZE].split('\t')]
           try:
              self.data = {}
              self.data['query'] = fields[self.fieldmap['query']]
              self.data['q_length'] = int(fields[self.fieldmap['q_length']])
              self.data['bitscore'] = float(fields[self.fieldmap['bitscore']])
              self.data['bsr'] = float(fields[self.fieldmap['bsr']])
              self.data['target'] = fields[self.fieldmap['target']]
              self.data['aln_length'] = float(fields[self.fieldmap['aln_length']])
              self.data['expect'] = float(fields[self.fieldmap['expect']])
              self.data['identity'] = float(fields[self.fieldmap['identity']])
              self.data['ec'] = fields[self.fieldmap['ec']]
              self.data['product'] = re.sub(r'=',' ',fields[self.fieldmap['product']])
           except:
              print "<<<<<<-------"
              print 'self size ' + str(self.size)
              print 'line ' + self.lines[self.i % self.SIZE]
              print 'index ' + str(self.i)
              print 'data ' + str(self.data)
              print ">>>>>>-------"
#              import traceback 
#              print traceback.print_exc()
              self.i = self.i + 1
              return None
           
           self.i = self.i + 1
           try:
              return self.data
           except:
              return None
        else:
           self.blastoutputfile.close()
           raise StopIteration()
              
def isWithinCutoffs(data, cutoffs):
  import traceback

  try:
    if data['q_length'] < cutoffs.min_length:
       return False

    if data['bitscore'] < cutoffs.min_score:
       return False

    if data['expect'] > cutoffs.max_evalue:
       return False

    if data['identity'] < cutoffs.min_identity:
       return False

    if data['bsr'] < cutoffs.min_bsr:
       return False
  except:
     print traceback.print_exc()
    # print cutoffs
     sys.exit(0)

  return True


# compute the refscores
def process_parsed_blastoutput(dbname, blastoutput, cutoffs, annotation_results):
    blastparser =  BlastOutputTsvParser(dbname, blastoutput)

    fields = ['target', 'q_length', 'bitscore', 'bsr', 'expect', 'identity', 'ec', 'query' ]
    fields.append('product')

    count = 0 
    for data in blastparser:
        if data!=None and isWithinCutoffs(data, cutoffs) :
           # if dbname=='refseq':
           # print data['query'] + '\t' + str(data['q_length']) +'\t' + str(data['bitscore']) +'\t' + str(data['expect']) +'\t' + str(data['identity']) + '\t' + str(data['bsr']) + '\t' + data['ec'] + '\t' + data['product']
           annotation = {}
           for field in fields:
             if field in data:
                annotation[field] = data[field] 
           annotation['dbname'] = dbname

           if not data['query'] in annotation_results:
               annotation_results[data['query']] = []

           annotation_results[data['query']].append(annotation)
        count += 1
       # if count%100==0:
       #    print count
    return None

def beginning_valid_field(line):
    fields = [ x.strip() for x in line.split('\t') ]
    count =0
    for field in fields:
       if len(field) > 0:
         return count
       count+=1

    return -1

def read_map_file(dbname_map_filename, field_to_description, hierarchical_map) :
    map_file = open(dbname_map_filename, 'r')
    map_filelines = map_file.readlines()
    
    tempfields = [ '', '', '', '', '', '', '' ]
    for line in map_filelines:
       pos = beginning_valid_field(line)
       if pos==-1: 
          continue

       fields = [ x.strip() for x in line.split('\t') ]
       
       tempfields[pos] = fields[pos]
       if len(fields) > pos + 1:
          field_to_description[fields[pos]] = fields[pos+1]
       else:
          field_to_description[fields[pos]] = fields[pos]
       
       i=0
       temp_hierarchical_map = hierarchical_map
       while i < pos :
          temp_hierarchical_map = temp_hierarchical_map[ tempfields[i] ]
          i+=1
     
       temp_hierarchical_map[ tempfields[i] ] = {}



def cog_id(product):
    results = re.search(r'COG[0-9][0-9][0-9][0-9]', product)
    cog_id = ''
    if results:
       cog_id=results.group(0)
    return cog_id
    

def kegg_id(product):
    results = re.search(r'K[0-9][0-9][0-9][0-9][0-9]', product)
    kegg_id = ''
    if results:
       kegg_id=results.group(0)
    return kegg_id

def create_table(results, dbname_map_filename, dbname, output_dir):
    if not path.exists(output_dir):
       makedirs(output_dir)

    field_to_description = {}
    hierarchical_map = {}
    read_map_file(dbname_map_filename, field_to_description, hierarchical_map)
    
    #print field_to_description
    orthology_count = {}
    for key in field_to_description:
       orthology_count[key] = 0 
    
    #print hierarchical_map 
    for seqname in results:    
       for orf in results[seqname]:
           if dbname =='cog': 
              cog =  cog_id(orf['product'])
              if cog in orthology_count:
                 orthology_count[cog]+=1

           if dbname =='kegg': 
              kegg =  kegg_id(orf['product'])
              if kegg in orthology_count:
                 orthology_count[kegg]+=1

    add_counts_to_hierarchical_map(hierarchical_map, orthology_count)

    if dbname=='cog':
       outputfile = open( output_dir +'/COG_stats_1.txt', 'w')
       print_counts_at_level(hierarchical_map, field_to_description,  0, 0, outputfile, printKey=False,\
          header="Functional Category\tGene Count") 
       outputfile.close()
       outputfile = open( output_dir +'/COG_stats_2.txt', 'w')
       print_counts_at_level(hierarchical_map, field_to_description,  0, 1, outputfile,\
          header="Function Abbr\tFunctional Category\tGene Count") 
       outputfile.close()
       outputfile = open( output_dir +'/COG_stats_3.txt', 'w')
       print_counts_at_level(hierarchical_map, field_to_description,  0, 2, outputfile,\
          header="COGID\tFunction\tGene Count") 
       outputfile.close()

    if dbname=='kegg':
       outputfile = open( output_dir +'/KEGG_stats_1.txt', 'w')
       print_counts_at_level(hierarchical_map, field_to_description,  0, 0, outputfile, printKey=False,\
          header="Function Category Level 1\tGene Count") 
       outputfile.close()
       outputfile = open( output_dir +'/KEGG_stats_2.txt', 'w')
       print_counts_at_level(hierarchical_map, field_to_description,  0, 1, outputfile, printKey=False,\
          header="Function Category Level 2a\tGene Count") 
       outputfile.close()
       outputfile = open( output_dir +'/KEGG_stats_3.txt', 'w')
       print_counts_at_level(hierarchical_map, field_to_description,  0, 2, outputfile,\
         header="ID\tFunction Category Level 3\tGene Count" ) 
       outputfile.close()
       outputfile = open( output_dir +'/KEGG_stats_4.txt', 'w')
       print_counts_at_level(hierarchical_map, field_to_description,  0, 3, outputfile,\
         header="KO\tFunction Category Level 4\tGene Count") 
       outputfile.close()



def print_counts_at_level(hierarchical_map, field_to_description,  depth, level, outputfile, printKey=True, header=None): 
    
    if type(hierarchical_map) is type(0):
       return hierarchical_map
    if header:
       fprintf(outputfile, "%s\n",header )

    count = 0
    for key in hierarchical_map:  
       tempcount = print_counts_at_level(hierarchical_map[key],field_to_description, depth+1, level, outputfile, printKey=printKey)
       if depth==level:
          if key in field_to_description:
              if printKey:
                 fprintf(outputfile, "%s\n", key + '\t' + field_to_description[key] + '\t' +  str(tempcount) )
              else:
                 fprintf(outputfile, "%s\n",  field_to_description[key] + '\t' +  str(tempcount) )
          else:
              if printKey:
                 fprintf(outputfile, "%s\n", key + '\t' + ' ' + '\t' + str(tempcount))
              else:
                 fprintf(outputfile, "%s\n", key +  '\t' + str(tempcount))
       count+=tempcount
    return count


def  add_counts_to_hierarchical_map(hierarchical_map, orthology_count):
     
    for key in hierarchical_map:  
       if len(hierarchical_map[key])==0:  
          if key in orthology_count:
            hierarchical_map[key]=int(orthology_count[key])
          else:
            hierarchical_map[key]=int(0)
       else:
          add_counts_to_hierarchical_map(hierarchical_map[key], orthology_count)
   
# the main function
def main(argv): 
    global parser
    (opts, args) = parser.parse_args(argv)
    if not check_arguments(opts, args):
       print usage
       sys.exit(0)

    results_dictionary={}
    dbname_weight={}
    #import traceback
    for dbname, blastoutput in zip( opts.database_name, opts.input_blastout):
        print "Processing database : " + dbname
        try:
           results_dictionary[dbname]={}
           process_parsed_blastoutput(dbname, blastoutput, opts, results_dictionary[dbname])
        except:
           import traceback
           traceback.print_exc()
           print "Error: " + dbname
           pass

    create_annotation(results_dictionary, opts.input_annotated_gff, opts.output_dir,\
         opts.ncbi_taxonomy_map, opts.lca_min_score, opts.lca_top_percent, opts.lca_min_support)

    # print results_dictionary['cog']
    for dbname in results_dictionary:
       if  dbname=='cog':
          create_table(results_dictionary[dbname], opts.input_cog_maps, 'cog', opts.output_dir)

       if  dbname=='kegg':
          create_table(results_dictionary[dbname], opts.input_kegg_maps, 'kegg', opts.output_dir)

    peg2subsystem = {} 
    # this feature is useless with the new refseq
    if opts.subsystems2peg_file:
       process_subsys2peg_file(peg2subsystem, opts.subsystems2peg_file)

    print_orf_table(results_dictionary, opts.output_dir)

def refseq_id(product):
    results = re.search(r'gi\|[0-9.]*', product)
    refseq_id = ''
    if results:
       refseq_id=results.group(0)
    return refseq_id


def process_subsys2peg_file(subsystems2peg, subsystems2peg_file):
     try:
         orgfile = open(subsystems2peg_file,'r')
     except IOError:
         print "Cannot open " + str(org_file)

     lines = orgfile.readlines()
     orgfile.close()
     for line in lines:
        hits = line.split('\t')
        if len(hits) > 2:
           subsystems2peg[hits[2]]=hits[1]
     try:
        orgfile.close()
     except:
         print "Cannot close " + str(org_file)
 
def print_orf_table(results, output_dir):
    if not path.exists(output_dir):
       makedirs(output_dir)
   
    outputfile = open( output_dir +'/ORF_annotation_table.txt', 'w')

    orf_dict = {}
    for dbname in results.iterkeys():
      for seqname in results[dbname]:
         for orf in results[dbname][seqname]:
           if not orf['query'] in orf_dict:
               orf_dict[orf['query']] = {}

           if dbname =='cog': 
              cog =  cog_id(orf['product'])
              orf_dict[orf['query']][dbname] = cog

           if dbname =='kegg': 
              kegg =  kegg_id(orf['product'])
              orf_dict[orf['query']][dbname] = kegg

           if dbname=='seed':
              seed =  orf['product']
              orf_dict[orf['query']][dbname] = re.sub(r'\[.*\]','', seed).strip()
             

           orf_dict[orf['query']]['contig'] = seqname

    for orfn in orf_dict:
       if 'cog' in orf_dict[orfn]:
          cogFn = orf_dict[orfn]['cog']
       else:
          cogFn = ""

       if 'kegg' in orf_dict[orfn]:
          keggFn = orf_dict[orfn]['kegg']
       else:
          keggFn = ""

       if 'metacyc' in orf_dict[orfn]:
          metacycPwy = orf_dict[orfn]['metacyc']
       else:
          metacycPwy = ""

       if 'seed' in orf_dict[orfn]:
          seedFn = orf_dict[orfn]['seed']
       else:
          seedFn = ""

       fprintf(outputfile, "%s\n", orfn + "\t" + orf_dict[orfn]['contig'] + '\t' + cogFn + '\t' + keggFn +'\t' + seedFn + '\t' + metacycPwy)

    outputfile.close() 

def MetaPathways_create_reports_fast(argv):       
    createParser()
    main(argv)
    return (0,'')

# the main function of metapaths
if __name__ == "__main__":
    createParser()
    main(sys.argv[1:])

