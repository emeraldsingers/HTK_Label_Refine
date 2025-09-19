#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob
from pathlib import Path

PHONEME_GROUPS = {
    'sibilants': ['s', 'z', 'sh', 'zh', 'ts', 'dz', 'ch', 'dj', 'x'],
    'vowels': ['a', 'e', 'i', 'o', 'u', "N"],
    'consonants': ['b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 't', 'v', 'w'],
    'liquids': ['l', 'r'],
    'nasals': ['m', 'n', 'ng'],
    'stops': ['p', 'b', 't', 'd', 'k', 'g'],
    'fricatives': ['f', 'v', 'th', 'dh', 's', 'z', 'sh', 'zh', 'h'],
    'silence': ['pau', 'sil', 'SP'],
    'special': ['cl', 'vf'],
}

def convert_htk_time_to_seconds(htk_time):
    return int(htk_time) * 1e-7

def convert_seconds_to_htk_time(seconds):
    return int(seconds / 1e-7)

def get_phoneme_group(phoneme):
    phoneme_lower = phoneme.lower()

    if phoneme_lower in PHONEME_GROUPS['silence']:
        return 'silence'
    
    for group_name, phonemes in PHONEME_GROUPS.items():
        if phoneme_lower in phonemes:
            return group_name
    
    return 'unknown'

def should_merge_phonemes(phoneme1, phoneme2, group1, group2):
    if group1 == group2:
        return True

    merge_rules = [
        ('vowels', 'vowels'),
        ('consonants', 'consonants'),
        ('silence', 'silence'),
        ('sibilants', 'sibilants'),
        ('liquids', 'liquids'),
        ('nasals', 'nasals'),
        ('stops', 'stops'),
        ('fricatives', 'fricatives'),
        ('special', 'special')
    ]
    
    return (group1, group2) in merge_rules or (group2, group1) in merge_rules

def parse_lab_file(filepath):
    labels = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split()
                if len(parts) >= 3:
                    start_time = int(parts[0])
                    end_time = int(parts[1])
                    phoneme = parts[2]
                    labels.append({
                        'start': start_time,
                        'end': end_time,
                        'phoneme': phoneme
                    })
    return labels

def merge_labels(labels, max_gap_seconds=0.1):
    if not labels:
        return labels
    
    merged = []
    current_label = labels[0].copy()
    current_group = get_phoneme_group(current_label['phoneme'])
    
    for i in range(1, len(labels)):
        next_label = labels[i]
        next_group = get_phoneme_group(next_label['phoneme'])
        
        gap_seconds = convert_htk_time_to_seconds(next_label['start'] - current_label['end'])
        
        if (gap_seconds <= max_gap_seconds and 
            should_merge_phonemes(current_label['phoneme'], next_label['phoneme'], 
                                current_group, next_group)):
            
            current_label['end'] = next_label['end']
            
            if current_group == 'silence' and next_group == 'silence':
                current_label['phoneme'] = 'SP'
            
        else:
            if current_group == 'silence':
                current_label['phoneme'] = 'SP'
            
            merged.append(current_label)
            current_label = next_label.copy()
            current_group = next_group
    
    if current_group == 'silence':
        current_label['phoneme'] = 'SP'
    merged.append(current_label)
    
    final_merged = []
    i = 0
    while i < len(merged):
        current_label = merged[i].copy()
        
        if current_label['phoneme'] == 'SP':
            j = i + 1
            while j < len(merged) and merged[j]['phoneme'] == 'SP':
                current_label['end'] = merged[j]['end']
                j += 1
            i = j
        else:
            i += 1
        
        final_merged.append(current_label)
    
    return final_merged

def write_lab_file(labels, filepath):
    with open(filepath, 'w', encoding='utf-8') as f:
        for label in labels:
            f.write(f"{label['start']} {label['end']} {label['phoneme']}\n")

def process_lab_files(input_dir, output_dir=None, max_gap_seconds=0.1):
    input_path = Path(input_dir)
    if output_dir is None:
        output_path = input_path / "refined_labels"
    else:
        output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    lab_files = list(input_path.glob("*.lab"))
    
    if not lab_files:
        print(f"No .lab files found in {input_dir}")
        return
    
    print(f"Found {len(lab_files)} .lab files")
    
    for lab_file in lab_files:
        print(f"Processing: {lab_file.name}")
        
        try:
            labels = parse_lab_file(lab_file)
            
            if not labels:
                print(f"  Empty file: {lab_file.name}")
                continue
            print(f"  Original labels: {len(labels)}")

            merged_labels = merge_labels(labels, max_gap_seconds)
            
            print(f"  After merging: {len(merged_labels)} labels")
            
            output_file = output_path / lab_file.name
            write_lab_file(merged_labels, output_file)
            
            print(f"  Saved: {output_file}")
            
        except Exception as e:
            print(f"  Error during processing {lab_file.name}: {e}")
    
    print(f"\nMerging completed. Results saved to: {output_path}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='HTK Label Refining Tool')
    parser.add_argument('input_dir', help='Path to the input directory containing .lab files')
    parser.add_argument('-o', '--output', help='Path to the output directory (optional), defaults to "refined_labels" in the input directory')
    parser.add_argument('-g', '--gap', type=float, default=0.1, 
                       help='Maximum gap between phonemes in seconds (default: 0.1)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_dir):
        print(f"Error: Folder {args.input_dir} does not exist")
        return
    
    process_lab_files(args.input_dir, args.output, args.gap)

if __name__ == "__main__":
    main()