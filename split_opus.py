#!/usr/bin/env python3
"""
Split Opus Script
Splits opus.txt into 10 equally-sized files (opus1.txt, opus2.txt, etc.)
"""

import os
import math

def split_opus_file():
    """Split opus.txt into 10 equally-sized files"""
    
    input_file = 'opus.txt'
    num_files = 10
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found!")
        return
    
    # Get file size
    file_size = os.path.getsize(input_file)
    chunk_size = math.ceil(file_size / num_files)
    
    print(f"Splitting {input_file} ({file_size:,} bytes) into {num_files} files")
    print(f"Target chunk size: {chunk_size:,} bytes ({chunk_size / 1024 / 1024:.2f} MB)")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    total_length = len(content)
    chunk_length = math.ceil(total_length / num_files)
    
    for i in range(num_files):
        start_pos = i * chunk_length
        end_pos = min((i + 1) * chunk_length, total_length)
        
        # Try to find a good break point (end of line) near the target end position
        if end_pos < total_length and i < num_files - 1:
            # Look for the next newline within 1000 characters
            search_start = max(end_pos - 500, start_pos)
            search_end = min(end_pos + 500, total_length)
            
            # Find the last newline in the search range
            newline_pos = content.rfind('\n', search_start, search_end)
            if newline_pos != -1 and newline_pos > start_pos:
                end_pos = newline_pos + 1  # Include the newline
        
        chunk_content = content[start_pos:end_pos]
        
        # Write chunk to file
        output_filename = f'opus{i + 1}.txt'
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(chunk_content)
        
        actual_size = len(chunk_content.encode('utf-8'))
        print(f"Created {output_filename}: {len(chunk_content):,} chars, {actual_size:,} bytes ({actual_size / 1024 / 1024:.2f} MB)")
    
    # Verify all chunks
    total_chars_written = 0
    total_bytes_written = 0
    
    for i in range(1, num_files + 1):
        filename = f'opus{i}.txt'
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            total_bytes_written += size
            
            with open(filename, 'r', encoding='utf-8') as f:
                chars = len(f.read())
                total_chars_written += chars
    
    print(f"\nVerification:")
    print(f"Original file: {file_size:,} bytes, {total_length:,} characters")
    print(f"Split files total: {total_bytes_written:,} bytes, {total_chars_written:,} characters")
    print(f"Match: {file_size == total_bytes_written and total_length == total_chars_written}")
    
    if file_size == total_bytes_written and total_length == total_chars_written:
        print("✅ Split completed successfully!")
    else:
        print("❌ Warning: File sizes don't match exactly")

if __name__ == "__main__":
    split_opus_file() 