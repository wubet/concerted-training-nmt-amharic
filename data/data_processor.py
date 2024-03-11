import os
import shutil
import argparse


def copy_file(source_file_path, destination_file_path):
    """
    Copy content of a file from original_path to destination_path based on conditions.
    """

    # Check if the source file exists
    if not os.path.exists(source_file_path):
        print(f"Source file {source_file_path} doesn't exist!")
        return

    # Copy the content
    shutil.copy2(source_file_path, destination_file_path)
    print(f"Data copied from {source_file_path} to {destination_file_path}")


def main(original_path, destination_dir, source_language_alias, target_language_alias, task):
    # Based on the conditions you provided, determine the destination filename
    source_file_extension = os.path.splitext(original_path)[1][1:]
    if source_file_extension == source_language_alias:
        destination_filename = f"{task}.{source_language_alias}2{target_language_alias}.in"
    else:
        destination_filename = f"{task}.{source_language_alias}2{target_language_alias}.out"

    # Check if the destination directory exists, if not, create it
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)

    # Construct full path for the destination
    destination_file_path = os.path.join(destination_dir, destination_filename)

    copy_file(original_path, destination_file_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--original_path', required=True,
                        help='Path of files storing original language sequences.')
    parser.add_argument('--destination_dir', required=True,
                        help='directory of files storing language transliteration sequences.')
    parser.add_argument('--source_language_alias', required=True,
                        help='alias used to represent the source language.')
    parser.add_argument('--target_language_alias', required=True,
                        help='alias used to represent the target language.')
    parser.add_argument('--task', required=True,
                        help='file task, train, test, validation/dev.')

    args = parser.parse_args()
    main(args.original_path, args.destination_dir, args.source_language_alias, args.target_language_alias, args.task)
