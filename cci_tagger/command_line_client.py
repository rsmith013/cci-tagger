'''
BSD Licence
Copyright (c) 2016, Science & Technology Facilities Council (STFC)
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice,
        this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice,
        this list of conditions and the following disclaimer in the
        documentation and/or other materials provided with the distribution.
    * Neither the name of the Science & Technology Facilities Council (STFC)
        nor the names of its contributors may be used to endorse or promote
        products derived from this software without specific prior written
        permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from datetime import datetime
import json
import sys
import time

from cci_tagger.tagger import ProcessDatasets


def get_datasets_from_file(file_name):
    """
    Get a list of datasets from the given file.

    @param file_name (str): the name of the file containing the list of
            datasets to process

    @return a List(str) of datasets

    """
    datasets = set()
    with open(file_name) as reader:
        for ds in reader.readlines():
            datasets.add(ds.strip())

    return datasets


def read_json_file(file_name):
    """
    Get the contents from the given json file.

    @param file_name (str): the name of the json file

    @return the contents of the json file

    """

    with open(file_name) as json_data:
        data = json.load(json_data)

    return data


class CCITaggerCommandLineClient(object):

    @staticmethod
    def parse_command_line():
        parser = ArgumentParser(
            description='Tag observations. You can tag an individual dataset, '
            'or tag all the datasets'
            '\nlisted in a file.',
            epilog='\n\nA number of files are produced as output:'
            '\n  esgf_drs.json contains a list of DRS and associated files '
            'and check sums'
            '\n  moles_tags.csv contains a list of dataset paths and '
            'vocabulary URLs'
            '\n  error.txt contains a list of errors'
            '\n\nExamples:'
            '\n  moles_esgf_tag -d /neodc/esacci/cloud/data/L3C/avhrr_noaa-16 '
            '-v'
            '\n  moles_esgf_tag -f datapath --file_count 2 --no_check_sum -v'
            '\n  moles_esgf_tag -j example.json -v'
            '\n  moles_esgf_tag -s',
            formatter_class=RawDescriptionHelpFormatter)

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '-d', '--dataset',
            help=('the full path to the dataset that is to be tagged. This '
                  'option is used to tag a single dataset.')
        )
        group.add_argument(
            '-f', '--file',
            help=('the name of the file containing a list of datasets to '
                  'process. This option is used for tagging one or more '
                  'datasets.')
        )
        group.add_argument(
            '-j', '--json_datasets',
            help=('use the json file for the list of datasets')
        )

        parser.add_argument(
            '--file_count',
            help='how many .nt files to look at per dataset',
            type=int, default=0
        )
        parser.add_argument(
            '--json_store',
            help='Directory containing the JSON config files for each dataset',
            required=True
        )
        parser.add_argument(
            '-v', '--verbose', action='count',
            help='increase output verbosity',
            default=0
        )

        args = parser.parse_args()
        datasets = None

        start_time = time.strftime("%H:%M:%S")

        # Read datasets from the command line
        if args.dataset is not None:
            if args.verbose >= 1:
                print(f"\n{start_time} STARTED")
                print("Processing {args.dataset}")
            datasets = {args.dataset}

        # Read list of datasets from a file
        elif args.file is not None:
            if args.verbose >= 1:
                print(f"\n{start_time} STARTED")
            datasets = get_datasets_from_file(args.file)

        # Given a json file, get the datasets from the datasets key
        elif args.json_datasets is not None:
            if args.verbose >= 1:
                print(f"\n{start_time} STARTED")

            json_data = read_json_file(args.json_datasets)
            datasets = json_data.get("datasets")

        return datasets, args

    @classmethod
    def main(cls):
        start_time = datetime.now()

        # Get the command line arguments
        datasets, args = cls.parse_command_line()

        # Quit of there are no datasets
        if datasets is None:
            print("You have not provided any datasets")
            sys.exit(0)

        pds = ProcessDatasets(verbose=args.verbose, json_directory=args.json_store)
        pds.process_datasets(datasets, args.file_count)

        if args.verbose >= 1:
            print("%s FINISHED\n\n" % (time.strftime("%H:%M:%S")))
            end_time = datetime.now()
            time_diff = end_time - start_time
            hours, remainder = divmod(time_diff.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            print('Time taken %02d:%02d:%02d' % (hours, minutes, seconds))

        exit(0)


if __name__ == "__main__":
    CCITaggerCommandLineClient.main()
