#!/usr/bin/env/python
"""
Usage:
    prepare_data_train.py [options]

Options:
    -h --help                Show this screen.
    --data_path FILE         Path to data file containing pairs of molecules
    --dataset_name NAME      Name of dataset (for use in output file naming)
    --save_dir NAME          Path to save directory
    --reverse                If true, add pairs in both orders
"""

import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rdkit import Chem
from rdkit.Chem import rdmolops
from rdkit.Chem import rdFMCS
import glob
import json
import numpy as np
from utils import bond_dict, dataset_info, need_kekulize, to_graph, to_graph_mol, graph_to_adj_mat
import utils
import pickle
import random
from docopt import docopt
from align_molecules import align_smiles_by_MCS_it

dataset = 'zinc' # Change to zinc_phosphorus if necessary

def read_file(file_path, reverse=False):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    num_lines = len(lines)
    data = []
    for i, line in enumerate(lines):
        toks = line.strip().split()
        if len(toks) == 1:
            smiles_1, smiles_2 = toks[0], toks[0]
            reverse=False # If only one molecule, don't allow pair in both orders
        else:
            smiles_1, smiles_2 = toks[0], toks[1]
        data.append({'smiles_1': smiles_1, 'smiles_2': smiles_2})
        if reverse:
            data.append({'smiles_1': smiles_2, 'smiles_2': smiles_1})
        if i % 2000 ==0:
            print('Finished reading: %d / %d' % (i, num_lines), end='\r')
    print('Finished reading: %d / %d' % (num_lines, num_lines))
    return data


def preprocess(raw_data, dataset, name, save_dir=''):
    print('Parsing smiles as graphs.')
    processed_data = []
    max_size = max(dataset_info(dataset)['bucket_sizes'])-1
    
    fails = 0
    total = len(raw_data)
    for i, (smiles_1, smiles_2) in enumerate([(mol['smiles_1'], mol['smiles_2']) for mol in raw_data]):
        (mol_in, mol_out), _, nodes_to_keep = align_smiles_by_MCS_it(smiles_1, smiles_2)
        if mol_out == []:
            fails +=1
            continue
        nodes_in, edges_in = to_graph_mol(mol_in, dataset)
        nodes_out, edges_out = to_graph_mol(mol_out, dataset)
        # Check molecule not too large
        if max(len(nodes_in), len(nodes_out)) > max_size:
            fails +=1
            continue
        if min(len(edges_in), len(edges_out)) <= 0:
            fails +=1
            continue
        processed_data.append({
                'graph_in': edges_in,
                'graph_out': edges_out,
                'node_features_in': nodes_in,
                'node_features_out': nodes_out,
                'smiles_out': smiles_2,
                'smiles_in': smiles_1,
                'v_to_keep': nodes_to_keep,
        })
        if i % 500 == 0:
            print('Processed: %d / %d' % (i, total), end='\r')
    print('Processed: %d / %d' % (total, total))
    if fails >0:
        print("Failed %d molecules" % fails)
    print("Saving data.")
    with open(save_dir+'molecules_%s.json' % name, 'w') as f:
        json.dump(processed_data, f)
    print('Length raw data: \t%d' % total)
    print('Length processed data: \t%d' % len(processed_data))

if __name__ == "__main__":
    # Parse args
    args = docopt(__doc__)
    
    reverse = args.get('--reverse')

    if args.get('--data_path') and args.get('--dataset_name'):
        data_paths = [args.get('--data_path')]
        names = [args.get('--dataset_name')]
    else:
        data_paths = ['data_zinc_dekois_train.smi', 'data_zinc_dekois_valid.smi', 'data_zinc_dude_train.smi', 'data_zinc_dude_valid.smi']
        names = ['zinc_dekois_train', 'zinc_dekois_valid', 'zinc_dude_train', 'zinc_dude_valid']
        reverse=True

    if args.get('--save_dir'):
        save_dir = args.get('--save_dir')
    else:
        save_dir = ''

    for data_path, name in zip(data_paths, names):
        print("Preparing %s" % data_path)
        raw_data = read_file(data_path, reverse=reverse)
        preprocess(raw_data, dataset, name, save_dir=save_dir)
