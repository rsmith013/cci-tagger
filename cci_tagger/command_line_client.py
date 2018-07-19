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
import sys
import time

from cci_tagger.mappings import LocalVocabMappings
from cci_tagger.tagger import ProcessDatasets


def get_datasets_from_file(file_name):
    """
    Get a list of datasets from the given file.

    @param file_name (str): the name of the file containing the list of
            datasets to process

    @return a List(str) of datasets

    """
    datasets = set()
    f = open(file_name, 'rb')
    for ds in f.readlines():
        datasets.add(ds.strip())
    return datasets


class CCITaggerCommandLineClient(object):

    def parse_command_line(self, argv):
        parser = ArgumentParser(
            description='Tag observations. You can tag an individual dataset, '
            'or tag all the datasets'
            '\nlisted in a file. By default a check sum will be '
            'produces for each file.',
            epilog='\n\nA number of files are produced as output:'
            '\n  esgf_drs.json contains a list of DRS and associated files '
            'and check sums'
            '\n  moles_tags.csv contains a list of dataset paths and '
            'vocabulary URLs'
            '\n  moles_esgf_mapping.csv contains mappings between dataset '
            'paths and DRS'
            '\n  error.txt contains a list of errors'
            '\n\nExamples:'
            '\n  moles_esgf_tag -d /neodc/esacci/cloud/data/L3C/avhrr_noaa-16 '
            '-v'
            '\n  moles_esgf_tag -f datapath --file_count 2 --no_check_sum -v'
            '\n  moles_esgf_tag -s'
            '\n\nDEFAULT_TERMS_FILE'
            '\n  This file should have the format of:'
            '\n    <property name>=<vocabulary term>'
            "\n\n  When <property name> is 'institution', 'platform', "
            "'sensor' or "
            "\n  'time_coverage_resolution' then <vocabulary term> may be a "
            "comma separated "
            "\n  list"
            '\n\n  For example:'
            '\n    ecv=soil moisture'
            '\n    processing_level=Level 4'
            '\n',
            formatter_class=RawDescriptionHelpFormatter)

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '-d', '--dataset',
            help=('the full path to the dataset that is to be tagged. This '
                  'option is used to tag a single dataset.'))
        group.add_argument(
            '-f', '--file',
            help=('the name of the file containing a list of datasets to '
                  'process. This option is used for tagging one or more '
                  'datasets.'))
        group.add_argument(
            '-s', '--show_mappings', action='store_true',
            help='show the local vocabulary mappings')

        parser.add_argument(
            '-m', '--use_mappings', action='store_true',
            help=('use the local vocabulary mappings. This will map a number '
                  'of non compliant terms to allowed terms.'))
        parser.add_argument(
            '-u', '--update_moles', action='store_true',
            help=('update the MOLEs catalogue directly rather than produce '
                  'a csv file.'))
        parser.add_argument(
            '-t', '--default_terms_file',
            help=("the name of the file containing a list of default "
                  "vocabulary terms to associate with a dataset. Property "
                  "values for 'institution', 'platform', 'sensor' and "
                  "'time_coverage_resolution' may be comma separated lists"))
        parser.add_argument(
            '--file_count',
            help='how many .nt files to look at per dataset',
            type=int, default=0)
        parser.add_argument(
            '--no_check_sum', action='store_true',
            help='do not produce a check sum for each file')
        parser.add_argument(
            '-v', '--verbose', action='count',
            help='increase output verbosity',
            default=0)

        args = parser.parse_args(argv[1:])
        datasets = None
        if args.dataset is not None:
            if args.verbose >= 1:
                print("\n%s STARTED" % (time.strftime("%H:%M:%S")))
                print("Processing %s" % args.dataset)
            datasets = set([args.dataset])
        elif args.file is not None:
            if args.verbose >= 1:
                print("\n%s STARTED" % (time.strftime("%H:%M:%S")))
            datasets = get_datasets_from_file(args.file)
        elif args.show_mappings:
            print(LocalVocabMappings())

        return datasets, args

    @classmethod
    def main(cls, argv=sys.argv):
        start_time = datetime.now()
        client = cls()
        datasets, args = client.parse_command_line(argv)
        if datasets is None:
            sys.exit(0)

        pds = ProcessDatasets(
            checksum=not(args.no_check_sum), use_mapping=args.use_mappings,
            verbose=args.verbose, update_moles=args.update_moles,
            default_terms_file=args.default_terms_file)
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
