#!/usr/bin/env python

from __future__ import print_function
from elfsize import add_node, output_to_file, default_op, default_datafile, default_peakfile, default_op_peak, repo_root
from collections import OrderedDict
from os import path
import re, bisect, json, csv
from subprocess import check_output
from pprint import pprint
import sys

#arm-none-eabi-nm -nl <elf file>
NM_EXEC = "arm-none-eabi-nm"
OPT = "-nl"
ptn = re.compile("([0-9a-f]*) ([Tt]) ([^\t\n]*)(?:\t(.*):([0-9]*))?")
func_mem_usage_map = {}
alloc_info = {}
module_alloc_info = {}
total_alloc_timeline = {}
current_total = 0
fnt = None

class ElfHelper(object):
    def __init__(self, p,m):
        if path.isfile(p):
            elf_path = p
        if path.isfile(m):
            map_path = m
        
        op = check_output([NM_EXEC, OPT, elf_path])
        map_file = open(map_path)
        self.maplines = map_file.readlines()
        self.matches = ptn.findall(op)
        self.addrs = [int(x[0],16) for x in self.matches]
        #print(self.maplines)
        
    def function_addrs(self):
        return self.addrs
    
    def function_name_for_addr(self, addr):
        i = bisect.bisect_right(self.addrs, addr)
        funcname = self.matches[i-1][2]
        return funcname

    def file_name_for_function_name(self, funcname):
        for eachline in self.maplines:
            #print("%s:%s"%(eachline,funcname))
            result = eachline.find(funcname)
            if(result != -1):
                break
        toks = eachline.split()   
        #print("%s:%s"%(str(funcname),str(toks)))
        if(len(toks) <= 0):
            print("WARN: Unable to find %s in map file"%(str(funcname)))
            #return funcname
            return ("%s [FUNCTION]"%(str(funcname)))
        else:    
            return toks[-1].replace("./BUILD/","").replace("/","\\")
            #return toks[-1]

def main(input,output,output_peak):
    global fnt
    global current_total
    global alloc_info
    global total_alloc_timeline
    current_total_index=0
        
    root = OrderedDict({"name": "mbed", "children": []})
    bar_root = OrderedDict({"name": "mbed", "children": []})
        
    with open(input) as f:
        for line in f:
            line=line.strip()
            
            try:
                if line.startswith('#m'):
                    l = re.findall(r"[\w']+", line)
                    l = [x.strip() for x in l if x != '']
                    tag, ptr, code, size = l
                    func_name = fnt.function_name_for_addr(int(code,16))
                                    
                    #add to the list with alloc details
                    if not(ptr in alloc_info.keys()):
                        alloc_info[ptr]=()
                        current_total = current_total + int(size)
                    else: 
                        print("WARN: Alloc Duplicate(malloc):%s:%s"%(str(ptr),str(size)))
                        
                    alloc_filename = fnt.file_name_for_function_name(func_name.strip())    
                    alloc_info[ptr]=(func_name.strip(),size,code,alloc_filename)
                    
                    #print("Alloc:%s:%s"%(alloc_filename,size))
                    #add to the module list with alloc details
                    if not(alloc_filename in module_alloc_info.keys()):
                        module_alloc_info[alloc_filename]=(0,0) #current_mem, max_mem_watermark
                    #print("Bef:%s"%str(module_alloc_info[alloc_filename]))    
                    module_alloc_info[alloc_filename]=(module_alloc_info[alloc_filename][0]+int(size),module_alloc_info[alloc_filename][1])
                    if(module_alloc_info[alloc_filename][0] > module_alloc_info[alloc_filename][1]):
                        module_alloc_info[alloc_filename] = (module_alloc_info[alloc_filename][0],module_alloc_info[alloc_filename][0])
                    #print("Af:%s"%str(module_alloc_info[alloc_filename]))    
                        
                if line.startswith('#f'):
                    l = re.findall(r"[\w']+", line)
                    l = [x.strip() for x in l if x != '']
                    tag, ret, code, ptr = l
                    
                    #remove from the list
                    if not(ptr in alloc_info.keys()):
                        if(ptr != "00000000"):
                            print("WARN: Unable to find %s being freed: %s"%(str(ptr),line))
                        else:     
                            print("WARN: Null %s being being freed: %s"%(str(ptr),line))
                    else:
                        fname,free_size,code,filename = alloc_info[ptr]
                        del alloc_info[ptr]
                        current_total = current_total - int(free_size)
                        
                        if not(filename in module_alloc_info.keys()):
                            print("WARN: Unable to find %s in module alloc info during free: %s"%(str(ptr),line))
                        else:
                            module_alloc_info[filename]=(module_alloc_info[filename][0]-int(free_size),module_alloc_info[filename][1])
                

                if line.startswith('#r'):
                    l = re.findall(r"[\w']+", line)
                    l = [x.strip() for x in l if x != '']
                    tag, new_ptr, code, old_ptr, size = l
                    
                    print(line)
                    #remove from the list
                    if not(old_ptr in alloc_info.keys()):
                        #We dont want to print this warning because realloc actually frees the old pointer and malloc-s new one before invoking the realloc trace callback, so this condition will always be activated and warning is mis-leading
                        #print("WARN: Unable to find %s being moved in realloc: %s"%(str(old_ptr),line)) - 
                        pass
                    else:
                        fname,free_size,code,filename = alloc_info[old_ptr]
                        del alloc_info[old_ptr]
                        current_total = current_total - int(free_size)
                        
                        if not(filename in module_alloc_info.keys()):
                            print("WARN: Unable to find %s in module alloc info(realloc): %s"%(str(old_ptr),line))
                        else:
                            module_alloc_info[alloc_filename]=(module_alloc_info[alloc_filename][0]-int(free_size),module_alloc_info[alloc_filename][1])
                    
                    #now add new ptr to the list
                    if not(new_ptr in alloc_info.keys()):
                        alloc_info[new_ptr]=()
                        current_total = current_total + int(size)
                    else: 
                        #We dont want to print this warning because realloc actually frees the old pointer and malloc-s new one before invoking the realloc trace callback, so this condition will always be activated and warning is mis-leading                
                        #print("WARN: Alloc Duplicate(realloc):%s:%s"%(str(new_ptr),str(size))) 
                        pass
                    alloc_filename = fnt.file_name_for_function_name(func_name.strip())    
                    alloc_info[new_ptr]=(func_name.strip(),size,code,alloc_filename)
                                    
                    #print("Alloc:%s:%s"%(alloc_filename,size))
                    #add to the module list with alloc details
                    if not(alloc_filename in module_alloc_info.keys()):
                        module_alloc_info[alloc_filename]=(0,0) #current_mem, max_mem_watermark
                    #print("Bef:%s"%str(module_alloc_info[alloc_filename]))    
                    module_alloc_info[alloc_filename]=(module_alloc_info[alloc_filename][0]+int(size),module_alloc_info[alloc_filename][1])
                    if(module_alloc_info[alloc_filename][0] > module_alloc_info[alloc_filename][1]):
                        module_alloc_info[alloc_filename] = (module_alloc_info[alloc_filename][0],module_alloc_info[alloc_filename][0])
                    #print("Af:%s"%str(module_alloc_info[alloc_filename]))    
                
                #We need not handle #c(calloc) because how calloc works is it first calls malloc and then does the memset
                #We dont care about memset and we are already handling malloc above            
                #if line.startswith('#c'):
                #    l = re.findall(r"[\w']+", line)
                #    l = [x.strip() for x in l if x != '']
                #    tag, ptr, code, value, size = l
                #    print(l)                
            except:
                print("Unexpected exception while parsing line: %s"%(str(line))) 
                
            #total_alloc_timeline[current_total_index]=(current_total,alloc_info)
            current_total_index=current_total_index+1
            #print(total_alloc_timeline)
            
            test_total = 0
            for eachaddr in alloc_info.keys():
                func_name,size,code,filename = alloc_info.get(eachaddr)
                test_total = test_total + int(size)   
            
            if(test_total != current_total):
                print("===========================================")
                print("MEMORY TOTAL MISMATCH: test_total:%d current_total=%d"%(test_total,current_total))
                print("===========================================")
                return
                
    for eachaddr in alloc_info.keys():
        func_name,size,code,filename = alloc_info.get(eachaddr)
        if not(func_name in func_mem_usage_map.keys()):
            func_mem_usage_map[func_name]=(0,"")
        #else:
        #    print("Found more entries for: %s"%(func_name))        
        func_mem_usage_map[func_name]=(func_mem_usage_map[func_name][0]+int(size), filename)    
            
    for eachentry in func_mem_usage_map.items():
        #print("%s  :  %s  "%(str(eachentry[1][1]),str(eachentry[1][0])))
        add_node(root, ("%s\\%s")%(str(eachentry[1][1]),str(eachentry[0])), eachentry[1][0])
    
    #print(module_alloc_info)    
    for k,v in module_alloc_info.items():
        #print("%s:%s:%s"%(str(k[k.rfind("\\"):]),str(v[0]),str(v[1])))
        #print("%s:%s:%s"%(k,str(v[0]),str(v[1])))
        if(k.rfind("\\")>0):
            add_node(bar_root,k[k.rfind("\\")+1:], v[1])  
        else:
            add_node(bar_root,k, v[1])  
        
    print("Total Memory: %s"%(current_total))    
    output_to_file(output, root, "mbed_map")
    output_to_file(output_peak, bar_root, "mbed_map_peak")
    
if __name__ == '__main__':
    import argparse, webbrowser
    
    parser = argparse.ArgumentParser(
        description='Analyse mbed memtrace output from stdin and generate a json data file for visualisation')

    def output_arg(s):
        if path.isdir(s):
            s = path.join(s, default_datafile)
        return open(s, "wb")

    # specify arguments
    parser.add_argument('-i','--input', metavar='<path to input file with memtrace output>', type=str,
                       help='path to input file')      
    parser.add_argument('-o', '--output',    type = output_arg,
                        help = 'path of output json, defaults to {}, default filename \
                        to {} if a folder is specified'.format(default_op, default_datafile),
                        default = default_op)
    parser.add_argument('-p', '--output_peakfile',    type = output_arg,
                        help = 'path of output peaks json, defaults to {}, default filename \
                        to {} if a folder is specified'.format(default_op_peak, default_peakfile),
                        default = default_op_peak)
    parser.add_argument('-b', '--browser',   action='store_true',
                        help = 'launch the pie chart visualisation in a browser')
    parser.add_argument('-e','--elfpath', metavar='<module or elf file path>', type=str,
                       help='path to elf file')             
    parser.add_argument('-m','--mappath', metavar='<map file path>', type=str,
                       help='path to map file')                                    

    # get and validate arguments
    args = parser.parse_args()
    
    p = args.elfpath
    m = args.mappath
    if not path.exists(p):
        print("Path does not exist")
        parser.print_usage()
        sys.exit(1)
    
    fnt = ElfHelper(p,m)
    
    # parse input and write to output
    main(args.input, args.output, args.output_peakfile)

    # close output file
    output_fn = path.abspath(args.output.name)
    args.output.close()

    print("[INFO] data written to", output_fn)

    if args.browser:
        uri = "file://" + path.join(repo_root, "index.html")
        print("[INFO] opening in browser", uri)
        webbrowser.open(uri, new=2)
