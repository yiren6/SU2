#!/usr/bin/env python

## \file compute_uncertainty.py
#  \brief Python script for performing model-form UQ for SST turbulence model
#  \author J. Mukhopadhaya
#  \version 6.2.0 "Falcon"
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
# Copyright 2012-2019, Francisco D. Palacios, Thomas D. Economon,
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

# imports
import numpy as np
from optparse import OptionParser
import os, sys, shutil, copy, os.path
sys.path.append(os.environ['SU2_RUN'])
import SU2

def main():
# Command Line Options
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="filename",
                      help="read config from FILE", metavar="FILE")
    parser.add_option("-n", "--partitions", dest="partitions", default=1,
                      help="number of PARTITIONS", metavar="PARTITIONS")
    parser.add_option("-u", "--underRelaxation", dest="uq_urlx", default=0.1,
                      help="under relaxation factor", metavar="UQ_URLX")
    parser.add_option("-b", "--deltaB", dest="uq_delta_b", default=1.0,
                      help="magnitude of perturbation", metavar="UQ_DELTA_B")

    (options, args)=parser.parse_args()
    options.partitions = int( options.partitions )
    # check the typecasting
    options.beta_delta = float( options.uq_delta_b )
    options.urlx = float(options.uq_urlx)

    # load config, start state
    config = SU2.io.Config(options.filename)
    state  = SU2.io.State()

    # find solution files if they exist
    state.find_files(config)

    # prepare config
    config.NUMBER_PART = options.partitions
    config.USING_UQ = 'YES'
    config.UQ_DELTA_B = options.beta_delta
    config.UQ_URLX = options.urlx
    config.UQ_PERMUTE = 'NO'


    # perform eigenvalue perturbations
    for comp in range(1,4):
        print "\n\n =================== Performing " + str(comp) + "  Component Perturbation =================== \n\n"

        # make copies
        konfig = copy.deepcopy(config)
        ztate  = copy.deepcopy(state)

	# set componentality
        konfig.UQ_COMPONENT = comp

        # send output to a folder
        folderName = str(comp)+'c/'
        if os.path.isdir(folderName):
           os.system('rm -R '+folderName)
        os.system('mkdir ' + folderName)
        sendOutputFiles(konfig, folderName)

        # run su2
        info = SU2.run.CFD(konfig)
        ztate.update(info)
	
	# Solution merging
    	konfig.SOLUTION_FILENAME = konfig.RESTART_FILENAME
    	info = SU2.run.merge(konfig)
    	ztate.update(info)


    print "\n\n =================== Performing p1c1 Component Perturbation =================== \n\n"

    # make copies
    konfig = copy.deepcopy(config)
    ztate  = copy.deepcopy(state)

    # set componentality
    konfig.UQ_COMPONENT = 1
    konfig.UQ_PERMUTE = 'YES'

    # send output to a folder
    folderName = 'p1c1/'
    if os.path.isdir(folderName):
       os.system('rm -R '+folderName)
    os.system('mkdir ' + folderName)
    sendOutputFiles(konfig, folderName)

    # run su2
    info = SU2.run.CFD(konfig)
    ztate.update(info)
    
    # Solution merging
    konfig.SOLUTION_FILENAME = konfig.RESTART_FILENAME
    info = SU2.run.merge(konfig)
    state.update(info)

    print "\n\n =================== Performing p1c2 Component Perturbation =================== \n\n"

    # make copies
    konfig = copy.deepcopy(config)
    ztate  = copy.deepcopy(state)

    # set componentality
    konfig.UQ_COMPONENT = 2
    konfig.UQ_PERMUTE = 'YES'

    # send output to a folder
    folderName = 'p1c2/'
    if os.path.isdir(folderName):
       os.system('rm -R '+folderName)
    os.system('mkdir ' + folderName)
    sendOutputFiles(konfig, folderName)

    # run su2
    info = SU2.run.CFD(konfig)
    ztate.update(info)

    # Solution merging
    konfig.SOLUTION_FILENAME = konfig.RESTART_FILENAME
    info = SU2.run.merge(konfig)
    ztate.update(info)

def sendOutputFiles( config, folderName = ''):
    config.CONV_FILENAME = folderName + config.CONV_FILENAME
    #config.BREAKDOWN_FILENAME = folderName + config.BREAKDOWN_FILENAME
    config.RESTART_FILENAME = folderName + config.RESTART_FILENAME
    config.VOLUME_FILENAME = folderName + config.VOLUME_FILENAME
    config.SURFACE_FILENAME = folderName + config.SURFACE_FILENAME


if __name__ == "__main__":
    main()
