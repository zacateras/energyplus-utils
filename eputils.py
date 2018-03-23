import pandas as pd
import re
import itertools
import shutil
import os

class IDFParameter:
    def __init__(self, name, values):
        self.name = name
        self.values = values
		
def write_parameter(f_output, p_name, p_values):
    f_output.write('Parametric:SetValueForRun,\n')
    f_output.write('    $%s,                      !- Name\n' % p_name)
    
    for i in range(0, len(p_values)-1):
        f_output.write('    %s,                       !- Value for Run %s\n' % (p_values[i], i))
    f_output.write('    %s;                       !- Value for Run %s\n' % (p_values[len(p_values)-1], i+1))
        
    f_output.write('\n')

def write_parameter_section(f_output, p_names, p_sets):
    f_output.write('!-   ===========  ALL OBJECTS IN CLASS: PARAMETRIC:SETVALUEFORRUN ===========\n')
    f_output.write('\n')
    
    for i in range(0, len(p_names)):
        write_parameter(f_output, p_names[i], [x[i] for x in p_sets])

def adjust_parameter_section(input_file, output_file, p_names, p_sets):
    f_input = open(input_file, 'r')
    f_output = open(output_file, 'w')

    for line in f_input:
        if 'PARAMETRIC:SETVALUEFORRUN' in line:
            write_parameter_section(f_output, p_names, p_sets)

            # skip input file parameter section (until the beginning of the next section)
            while(True):
                line = next(f_input)
                if('!-   ===========' in line):
                    break

        f_output.write(line)

    f_input.close()
    f_output.close()
    
def invoke_ep(idf_file):
    ep_base_path = 'C:\\EnergyPlusV8-8-0'
    ep_app_path = os.path.join(ep_base_path, 'energyplus.exe')
    ep_pp_path = os.path.join(ep_base_path, 'PreProcess\\ParametricPreProcessor\\parametricpreprocessor.exe')

    # ep requires cwd to be the same as processed file
    cwd = os.getcwd()
    os.chdir(os.path.dirname(idf_file))

    # invoke parameter preprocessor
    cmd = '%s %s' % (ep_pp_path, idf_file)
    print(cmd)
    os.system(cmd)

    # TODO this could be parallelized
    for name in filter(lambda p: re.match('.*-[0-9]+.idf$', p), os.listdir('.')):
        dir_name = os.path.splitext(os.path.basename(name))[0]
        cmd = '%s --output-directory %s --readvars -s D %s' % (ep_app_path, dir_name, name)
        print(cmd)
        os.system(cmd)

    os.chdir(cwd)
    
def combine_result(p_names, p_sets, input_file_basename, tmp_dir, tmp_input_file_basename, output_dir):
    for set_i in range(0, len(p_sets)):
        dir_path = '%s-%s' % (tmp_input_file_basename, str(set_i + 1).zfill(6))
        csv_path = os.path.join(tmp_dir, dir_path, 'eplus.csv')
        df = pd.read_csv(csv_path)
    
        for p_i in range(0, len(p_names)):
            kwargs = { p_names[p_i]: p_sets[set_i][p_i] }
            df = df.assign(**kwargs)
    
        if set_i == 0:
            base_df = df
        else:
            base_df = pd.concat([base_df, df])

    create_dir(output_dir)
    base_df.to_csv(os.path.join(output_dir, ('%s.csv' % input_file_basename))) 
    
def create_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)
    
def recreate_dir(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)

def remove_dir(path):
    if os.path.exists(path):
        shutil.rmtree(path)
        
def evaluate_params(input_file, output_dir, params):
    input_file_basename = os.path.splitext(os.path.basename(input_file))[0]
    tmp_input_file = '%s.tmp.idf' % input_file_basename
    tmp_input_file_basename = os.path.splitext(os.path.basename(tmp_input_file))[0]
    tmp_dir = os.path.abspath('tmp')
    output_dir = os.path.abspath(output_dir)

    p_names = list([p.name for p in params])
    p_sets = list(itertools.product(*[p.values for p in params]))

    print('Preprocessing...')
    recreate_dir(tmp_dir)
    adjust_parameter_section(input_file, '%s/%s' % (tmp_dir, tmp_input_file), p_names, p_sets)

    print('Processing...')
    invoke_ep(os.path.join(tmp_dir, tmp_input_file))

    print('Postprocessing...')
    combine_result(p_names, p_sets, input_file_basename, tmp_dir, tmp_input_file_basename, output_dir)
    remove_dir(tmp_dir)

    print('Finished!')