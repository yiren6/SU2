#!/usr/bin/env python

## \file amg.py
#  \brief python package for running mesh adaptation using the AMG Inria library
#  \author Victorien Menier, Brian Mungu\'ia
#  \version 7.0.3 "Blackbird"
#
# The current SU2 release has been coordinated by the
# SU2 International Developers Society <www.su2devsociety.org>
# with selected contributions from the open-source community.
#
# The main research teams contributing to the current release are:
#  - Prof. Juan J. Alonso's group at Stanford University.
#  - Prof. Piero Colonna's group at Delft University of Technology.
#  - Prof. Nicolas R. Gauger's group at Kaiserslautern University of Technology.
#  - Prof. Alberto Guardone's group at Polytechnic University of Milan.
#  - Prof. Rafael Palacios' group at Imperial College London.
#  - Prof. Vincent Terrapon's group at the University of Liege.
#  - Prof. Edwin van der Weide's group at the University of Twente.
#  - Lab. of New Concepts in Aeronautics at Tech. Institute of Aeronautics.
#
# Copyright 2012-2018, Francisco D. Palacios, Thomas D. Economon,
#                      Tim Albring, and the SU2 contributors.
#
# SU2 is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# SU2 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with SU2. If not, see <http://www.gnu.org/licenses/>.

import os, sys, shutil, copy, time
import numpy as np

from .. import io   as su2io
from .. import amginria as su2amg
from .interface import CFD as SU2_CFD

import _amgio as amgio

def amg ( config , kind='' ):
    
    sys.stdout.write("SU2-AMG Anisotropic Mesh Adaptation\n")
        
    #--- Check config options related to mesh adaptation
    
    adap_options = ['PYADAP_COMPLEXITY', 'PYADAP_SUBITE', 'PYADAP_SENSOR', \
    'PYADAP_BACK', 'PYADAP_HMAX', 'PYADAP_HMIN', 'PYADAP_ARMAX', 'PYADAP_HGRAD', \
    'PYADAP_RESIDUAL_REDUCTION', 'PYADAP_FLOW_ITER', 'PYADAP_ADJ_ITER', 'PYADAP_CFL', \
    'PYADAP_INV_VOL', 'PYADAP_ORTHO', 'PYADAP_RDG', 'PYADAP_PYTHON']
    required_options = ['PYADAP_COMPLEXITY', 'PYADAP_SUBITE', \
    'PYADAP_SENSOR', 'MESH_FILENAME', 'RESTART_SOL', 'MESH_OUT_FILENAME']
    
    if not all (opt in config for opt in required_options):
        err = '\n\n## ERROR : Missing options: \n'
        for opt in required_options:
            if not opt in config:
                err += opt + '\n'
        raise AttributeError(err)
    
    #--- Print adap options

    sys.stdout.write(su2amg.print_adap_options(config, adap_options))
    
    #--- How many iterative loops? Using what prescribed mesh sizes? 
    
    mesh_sizes   = su2amg.get_mesh_sizes(config)
    sub_iter     = su2amg.get_sub_iterations(config)
    
    #--- Solver iterations/ residual reduction param for each size level

    adap_flow_iter = su2amg.get_flow_iter(config)
    adap_adj_iter  = su2amg.get_adj_iter(config)
    adap_flow_cfl  = su2amg.get_flow_cfl(config)
    adap_adj_cfl   = su2amg.get_flow_cfl(config)
    # adap_res       = su2amg.get_residual_reduction(config)

    adap_sensor = config.PYADAP_SENSOR
    sensor_avail = ['MACH', 'PRES', 'MACH_PRES', 'GOAL']
    
    if adap_sensor not in sensor_avail:
        raise ValueError('Unknown adaptation sensor (PYADAP_SENSOR option).\n')
        
    if len(mesh_sizes) != len(sub_iter):
        raise ValueError('Inconsistent number of mesh sizes and sub-iterations.\n \
                          %d mesh sizes and %d sub-iterations provided.' % (len(mesh_sizes),len(sub_iter)))
        
        
    #--- Use the python interface to amg, or the executable?
    
    amg_python = su2amg.get_python_amg(config)
    
    #--- Change current directory
    
    warn = False
    adap_dir = './adap'
    cwd = os.getcwd()
        
    if os.path.exists(adap_dir):
        sys.stdout.write('./adap exists. Removing old mesh adaptation in 10s.\n')
        sys.stdout.flush()
        if warn : time.sleep(10)
        shutil.rmtree(adap_dir)
    
    os.makedirs(adap_dir)
    os.chdir(adap_dir)
    sys.stdout.write('The %s folder was deleted\n' % adap_dir)
    sys.stdout.flush()
    
    cur_dir = './ini'
    os.makedirs(cur_dir)
    os.chdir(cur_dir)
    os.symlink(os.path.join(cwd, config.MESH_FILENAME), config.MESH_FILENAME)
        
    cur_meshfil = config['MESH_FILENAME']

    #--- Format of history file

    history_format = config.TABULAR_FORMAT
    if (history_format == 'TECPLOT'):
        history_filename = os.path.join(cwd,'history_adap.dat')
    else:
        history_filename = os.path.join(cwd,'history_adap.csv')

    #--- AMG parameters
    
    config_amg = dict()
    
    if 'PYADAP_HGRAD' in config: config_amg['hgrad'] = float(config['PYADAP_HGRAD'])

    config_amg['hmax']        = float(config['PYADAP_HMAX'])
    config_amg['hmin']        = float(config['PYADAP_HMIN'])
    config_amg['Lp']          = float(config['ADAP_NORM'])
    config_amg['mesh_in']     = 'current.meshb'
    config_amg['amg_log']     = 'amg.out'
    config_amg['adap_source'] = ''

    #--- Get mesh dimension

    dim = su2amg.get_su2_dim(cur_meshfil)
    if ( dim != 2 and dim != 3 ):
        raise ValueError("Wrong dimension number\n")
    
    #--- Generate background surface mesh

    if 'PYADAP_BACK' in config:
        config_amg['adap_back'] = os.path.join(cwd,config['PYADAP_BACK'])
        if not config['PYADAP_BACK'] == config['MESH_FILENAME']:
            os.symlink(os.path.join(cwd, config.PYADAP_BACK), config.PYADAP_BACK)
    else:
        config_amg['adap_back'] = config['MESH_FILENAME']
    
    back_name, back_extension = os.path.splitext(config_amg['adap_back'])
    
    if not os.path.exists(config_amg['adap_back']):
        raise Exception("\n\n##ERROR : Can't find back mesh: %s.\n\n" % config_amg['adap_back'])
    
    if back_extension == ".su2":
        sys.stdout.write("\nGenerating GMF background surface mesh.\n")
        sys.stdout.flush()
        amgio.py_ConvertSU2toInria(config_amg['adap_back'], "", "amg_back")
        config_amg['adap_back'] = os.path.join(cwd, "adap/ini/amg_back.meshb")

    #--- Remesh options: background surface mesh
    config_amg['options'] = "-back " + config_amg['adap_back']

    #--- Remesh options: invert background mesh
    if 'PYADAP_INV_BACK' in config:
        if(config['PYADAP_INV_BACK'] == 'YES'):
            config_amg['options'] = config_amg['options'] + ' -inv-back'

    #--- Remesh options: metric orthogonal adaptation
    if 'PYADAP_ORTHO' in config:
        if(config['PYADAP_ORTHO'] == 'YES'):
            config_amg['options'] = config_amg['options'] + ' -cart3d-only'

    #--- Remesh options: ridge detection
    if 'PYADAP_RDG' not in config:
        config_amg['options'] = config_amg['options'] + ' -nordg'
    else:
        if(config['PYADAP_RDG'] == 'NO'):
            config_amg['options'] = config_amg['options'] + ' -nordg'

    #--- Compute initial solution if needed, else link current files
    
    config_cfd = copy.deepcopy(config)
    for opt in adap_options:
        config_cfd.pop(opt, None)

    #--- Only write CSV if both WRT_BINARY and READ_BINARY exist and are set to NO
    sol_ext = ".dat"
    if ('WRT_BINARY_RESTART' in config) and ('READ_BINARY_RESTART' in config):
        if (config_cfd.WRT_BINARY_RESTART == "NO") and (config_cfd.READ_BINARY_RESTART == "NO"):
            sol_ext = ".csv"

    config_cfd.VOLUME_OUTPUT = "COORDINATES, SOLUTION, PRIMITIVE"
        
    if config['RESTART_SOL'] == 'NO':
        
        stdout_hdl = open('su2.out','w') # new targets
        stderr_hdl = open('su2.err','w')
        
        success = False
        val_out = [False]
        
        sys.stdout.write('Running initial CFD solution.\n')
        sys.stdout.flush()
        
        try: # run with redirected outputs
            
            sav_stdout, sys.stdout = sys.stdout, stdout_hdl 
            sav_stderr, sys.stderr = sys.stderr, stderr_hdl
        
            cur_meshfil = config['MESH_FILENAME']
            cur_solfil  = "restart_flow" + sol_ext
            
            config_cfd.CONV_FILENAME    = "history"
            config_cfd.RESTART_FILENAME = cur_solfil
            config_cfd.HISTORY_OUTPUT   = ['ITER', 'RMS_RES', 'AERO_COEFF', 'FLOW_COEFF', 'CFL_NUMBER']
            config_cfd.COMPUTE_METRIC   = 'NO'
            config_cfd.MATH_PROBLEM     = 'DIRECT'
            
            SU2_CFD(config_cfd)

            #--- Set RESTART_SOL=YES for runs after adaptation
            config_cfd.RESTART_SOL = 'YES'
                        
            if adap_sensor == 'GOAL':
                config_cfd_ad = copy.deepcopy(config)

                cur_solfil_adj = "restart_adj" + sol_ext

                config_cfd_ad.CONV_FILENAME        = "history_adj"
                config_cfd_ad.RESTART_ADJ_FILENAME = cur_solfil_adj
                config_cfd_ad.SOLUTION_FILENAME    = cur_solfil
                config_cfd_ad.MATH_PROBLEM         = 'DISCRETE_ADJOINT'
                config_cfd_ad.VOLUME_OUTPUT        = "COORDINATES, SOLUTION, PRIMITIVE, METRIC"
                config_cfd_ad.HISTORY_OUTPUT       = ['ITER', 'RMS_RES', 'SENSITIVITY']
                config_cfd_ad.COMPUTE_METRIC       = 'YES'
                config_cfd_ad.ADAP_HMAX            = config.PYADAP_HMAX
                config_cfd_ad.ADAP_HMIN            = config.PYADAP_HMIN
                config_cfd_ad.ADAP_ARMAX           = config.PYADAP_ARMAX
                config_cfd_ad.ADAP_COMPLEXITY      = int(mesh_sizes[0])

                cfl = su2amg.get_min_cfl(history_format)
                cfl = max(cfl, float(config.CFL_NUMBER))
                su2amg.set_cfl(config_cfd_ad, cfl)

                if (config.KIND_TURB_MODEL != 'NONE'):
                    cfl_turb = su2amg.get_min_cfl_turb(history_format)
                    cfl_red  = cfl_turb/cfl
                    config_cfd_ad.CFL_REDUCTION_TURB = float(cfl_red)

                SU2_CFD(config_cfd_ad)

                func_name      = config.OBJECTIVE_FUNCTION
                suffix         = su2io.get_adjointSuffix(func_name)
                cur_solfil_adj = su2io.add_suffix(cur_solfil_adj,suffix)

                #--- Set RESTART_SOL=YES for runs after adaptation
                config_cfd_ad.RESTART_SOL = 'YES'

        except:
            sys.stdout = sav_stdout
            sys.stderr = sav_stderr
            raise
        
        sys.stdout = sav_stdout
        sys.stderr = sav_stderr
        
    else:
        required_options=['SOLUTION_FILENAME','SOLUTION_ADJ_FILENAME']
        if not all (opt in config for opt in required_options):
            err = '\n\n## ERROR : RESTART_SOL is set to YES, but the solution is missing:\n'
            for opt in required_options:
                if not opt in config:
                    err += opt + '\n'
            raise AttributeError(err)

        os.symlink(os.path.join(cwd, config.SOLUTION_FILENAME), config.SOLUTION_FILENAME)

        sys.stdout.write('Initial CFD solution is provided.\n')
        sys.stdout.flush()

        stdout_hdl = open('su2.out','w') # new targets
        stderr_hdl = open('su2.err','w')

        success = False
        val_out = [False]

        sav_stdout, sys.stdout = sys.stdout, stdout_hdl 
        sav_stderr, sys.stderr = sys.stderr, stderr_hdl

        cur_meshfil    = config['MESH_FILENAME']
        cur_solfil     = "restart_flow" + sol_ext
        cur_solfil_adj = "restart_adj" + sol_ext

        #--- Run an iteration of the flow to get history info
        config_cfd.ITER             = 1
        config_cfd.CONV_FILENAME    = "history"
        config_cfd.RESTART_FILENAME = cur_solfil
        config_cfd.HISTORY_OUTPUT   = ['ITER', 'RMS_RES', 'AERO_COEFF', 'FLOW_COEFF', 'CFL_NUMBER']
        config_cfd.COMPUTE_METRIC   = 'NO'
        config_cfd.MATH_PROBLEM     = 'DIRECT'

        SU2_CFD(config_cfd)

        if adap_sensor == 'GOAL':
            config_cfd_ad = copy.deepcopy(config)

            config_cfd_ad.CONV_FILENAME         = "history_adj"
            config_cfd_ad.RESTART_FILENAME      = cur_solfil
            config_cfd_ad.RESTART_ADJ_FILENAME  = cur_solfil_adj
            config_cfd_ad.SOLUTION_FILENAME     = config['SOLUTION_FILENAME']
            config_cfd_ad.SOLUTION_ADJ_FILENAME = config['SOLUTION_ADJ_FILENAME']
            config_cfd_ad.VOLUME_OUTPUT         = "COORDINATES, SOLUTION, PRIMITIVE, METRIC"
            config_cfd_ad.HISTORY_OUTPUT        = ['ITER', 'RMS_RES', 'SENSITIVITY']
            config_cfd_ad.COMPUTE_METRIC        = 'YES'
            config_cfd_ad.MATH_PROBLEM          = 'DISCRETE_ADJOINT'
            config_cfd_ad.ADAP_HMAX             = config.PYADAP_HMAX
            config_cfd_ad.ADAP_HMIN             = config.PYADAP_HMIN
            config_cfd_ad.ADAP_ARMAX            = config.PYADAP_ARMAX
            config_cfd_ad.ADAP_COMPLEXITY       = int(mesh_sizes[0])

            #--- Run an adjoint if the adjoint solution file doesn't exist
            cur_solfil_adj_ini = config_cfd_ad.SOLUTION_ADJ_FILENAME    
            func_name          = config.OBJECTIVE_FUNCTION
            suffix             = su2io.get_adjointSuffix(func_name)
            cur_solfil_adj_ini = su2io.add_suffix(cur_solfil_adj_ini,suffix)
            if not (os.path.exists(os.path.join(cwd, cur_solfil_adj_ini))):
                config_cfd_ad.ITER        = config.ITER
                config_cfd_ad.RESTART_SOL = 'NO'

                SU2_CFD(config_cfd_ad)

                cur_solfil_adj = su2io.add_suffix(cur_solfil_adj,suffix)

                #--- Set RESTART_SOL=YES for runs after adaptation
                config_cfd_ad.RESTART_SOL = 'YES'

            #--- Otherwise just compute the metric
            else:
                os.symlink(os.path.join(cwd, cur_solfil_adj_ini), cur_solfil_adj_ini)
                config_cfd_ad.ITER = 1

                SU2_CFD(config_cfd_ad)

                sav_stdout.write('Initial adjoint CFD solution is provided.\n')
                sav_stdout.flush()

                cur_solfil_adj = cur_solfil_adj_ini

        sys.stdout = sav_stdout
        sys.stderr = sav_stderr
        
    #--- Check existence of initial mesh, solution
    
    required_files = [cur_meshfil,cur_solfil]
    
    if not all (os.path.exists(fil) for fil in required_files):
        err = '\n\n## ERROR : Can\'t find:\n'
        for fil in required_files:
            if not os.path.exists(fil):
                err += fil + '\n'
        raise Exception(err)
    
    #--- Start adaptive loop

    global_iter = 0

    #--- Print convergence history

    npoin = su2amg.get_su2_npoin(cur_meshfil)
    su2amg.plot_results(history_format, history_filename, global_iter, npoin)
    
    sys.stdout.write("\nStarting mesh adaptation process.\n")
    sys.stdout.flush()
    
    for iSiz in range(len(mesh_sizes)):
        
        mesh_size = int(mesh_sizes[iSiz])
        nSub      = int(sub_iter[iSiz])
                        
        sys.stdout.write("\nIteration %d - Mesh size coefficient %.1lf\n" % (iSiz, mesh_size))
        sys.stdout.flush()
        
        for iSub in range(nSub):
            
            # Prints
            pad_cpt = ("(%d/%d)" % (iSub+1, nSub)).ljust(9)
            pad_nul = "".ljust(9)
            
            #--- Load su2 mesh 
            
            mesh = su2amg.read_mesh_and_sol(cur_meshfil, cur_solfil)

            #--- Write solution
            su2amg.write_mesh_and_sol("flo.meshb", "flo.solb", mesh)

            config_amg['size'] = mesh_size
                
            #--- Use pyAmg interface
            
            try :
                import pyamg 
            except:
                sys.stderr.write("## ERROR : Unable to import pyamg module.\n")
                sys.exit(1)
            
            if adap_sensor == 'GOAL':

                #--- Use metric computed from SU2 to drive the adaptation

                metric_wrap = su2amg.create_sensor(mesh, adap_sensor)
                mesh['metric'] = metric_wrap['solution']

                #--- Read and merge adjoint solution to be interpolated

                sol_adj = su2amg.read_sol(cur_solfil_adj, mesh)
                su2amg.merge_sol(mesh, sol_adj)

                del sol_adj

            else:        

                #--- Create sensor used to drive the adaptation  

                sensor_wrap = su2amg.create_sensor(mesh, adap_sensor)
                mesh['sensor'] = sensor_wrap['solution']
                
            #--- Call pyAMG

            sys.stdout.write(' %s Generating adapted mesh using AMG\n' % pad_cpt)
            sys.stdout.flush()
            
            mesh_new = su2amg.call_pyamg(mesh, config_amg)

            #--- Remove extra files generated by AMG

            extra_files=['back.meshb','meshp3_smoo.meshb','optim.0.meshb','optim.0.solb','subdom.meshb']
            for file in extra_files:
                try:
                    os.remove(file)
                except OSError:
                    pass
                            
            #--- print mesh size
            
            sys.stdout.write(' %s AMG done: %s\n' % (pad_nul, su2amg.return_mesh_size(mesh_new)))
            sys.stdout.flush()

            mesh_new['markers'] = mesh['markers']
            mesh_new['dimension'] = mesh['dimension']
            mesh_new['solution_tag'] = mesh['solution_tag']

            del mesh

            old_dir = cur_dir
            cur_dir = './ite%d' % (global_iter)
            os.makedirs(os.path.join('..',cur_dir))
            os.chdir(os.path.join('..',cur_dir))
            
            cur_meshfil = "adap.su2"
            cur_solfil  = "flo" + sol_ext
                            
            su2amg.write_mesh_and_sol(cur_meshfil, cur_solfil, mesh_new)

            if adap_sensor == 'GOAL':
                cur_solfil_adj = "adj" + sol_ext
                sol_adj = su2amg.split_adj_sol(mesh_new)
                su2amg.write_sol(cur_solfil_adj, sol_adj)

            cur_meshfil_gmf    = "flo_itp.meshb"
            cur_solfil_gmf     = "flo_itp.solb"
            su2amg.write_mesh_and_sol(cur_meshfil_gmf, cur_solfil_gmf, mesh_new)

            del mesh_new

            if adap_sensor == 'GOAL':
                cur_solfil_gmf_adj = "adj_itp.solb"
                su2amg.write_sol(cur_solfil_gmf_adj, sol_adj)
                del sol_adj
                
            #--- Run su2
            
            stdout_hdl = open('su2.out','w') # new targets
            stderr_hdl = open('su2.err','w')
            
            success = False
            val_out = [False]
            
            sys.stdout.write(' %s Running CFD\n' % pad_nul)
            sys.stdout.flush()
        
            try: # run with redirected outputs
            
                sav_stdout, sys.stdout = sys.stdout, stdout_hdl 
                sav_stderr, sys.stderr = sys.stderr, stderr_hdl
                
                cur_solfil_ini = "flo_ini" + sol_ext
                os.rename(cur_solfil, cur_solfil_ini)

                if adap_sensor == 'GOAL':
                    cur_solfil_adj_ini = "adj_ini" + sol_ext
                    cur_solfil_adj_ini = su2io.add_suffix(cur_solfil_adj_ini,suffix)
                    os.rename(cur_solfil_adj, cur_solfil_adj_ini)
                    cur_solfil_adj_ini = "adj_ini" + sol_ext
                
                config_cfd.MESH_FILENAME     = cur_meshfil
                config_cfd.SOLUTION_FILENAME = cur_solfil_ini
                config_cfd.RESTART_FILENAME  = cur_solfil
                config_cfd.ITER              = int(adap_flow_iter[iSiz])

                su2amg.set_cfl(config_cfd, adap_flow_cfl[iSiz])
                
                SU2_CFD(config_cfd)
                
                if not os.path.exists(cur_solfil) :
                    raise Exception("\n##ERROR : SU2_CFD Failed.\n")
                    
                if adap_sensor == 'GOAL':

                    config_cfd_ad.MESH_FILENAME          = cur_meshfil
                    config_cfd_ad.RESTART_ADJ_FILENAME   = cur_solfil_adj
                    config_cfd_ad.SOLUTION_ADJ_FILENAME  = cur_solfil_adj_ini
                    config_cfd_ad.SOLUTION_FILENAME      = cur_solfil
                    config_cfd_ad.RESTART_FILENAME       = cur_solfil
                    config_cfd_ad.ITER                   = int(adap_adj_iter[iSiz])
                    config_cfd_ad.ADAP_COMPLEXITY        = int(mesh_sizes[iSiz])

                    cfl = su2amg.get_min_cfl(history_format)
                    cfl = max(cfl, adap_flow_cfl[iSiz])
                    su2amg.set_cfl(config_cfd_ad, cfl)

                    if (config.KIND_TURB_MODEL != 'NONE'):
                        cfl_turb = su2amg.get_min_cfl_turb(history_format)
                        cfl_red  = cfl_turb/cfl
                        config_cfd_ad.CFL_REDUCTION_TURB = float(cfl_red)

                    SU2_CFD(config_cfd_ad)

                    cur_solfil_adj = su2io.add_suffix(cur_solfil_adj,suffix)

                    if not os.path.exists(cur_solfil_adj) :
                        raise Exception("\n##ERROR : SU2_CFD_AD Failed.\n")
            
            except:
                sys.stdout = sav_stdout
                sys.stderr = sav_stderr
                raise
            
            sys.stdout = sav_stdout
            sys.stderr = sav_stderr
            
                    
            #--- Print convergence history

            global_iter += 1
            npoin = su2amg.get_su2_npoin(cur_meshfil)
            su2amg.plot_results(history_format, history_filename, global_iter, npoin)
            

    #--- Write final files

    mesh = su2amg.read_mesh_and_sol(cur_meshfil, cur_solfil)
    su2amg.write_mesh_and_sol("flo.meshb", "flo.solb", mesh)
    
    os.rename(cur_solfil,os.path.join(cwd,config.RESTART_FILENAME))
    os.rename(cur_meshfil,os.path.join(cwd,config.MESH_OUT_FILENAME))
    
    sys.stdout.write("\nMesh adaptation successfully ended. Results files:\n")
    sys.stdout.write("%s\n%s\n\n" % (config.MESH_OUT_FILENAME,config.RESTART_FILENAME))
    sys.stdout.flush()
    