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
import csv
from datetime import datetime
import sys
import time

from cci_tagger.settings import MOLES_TAGS_FILE, MOLES_ESGF_MAPPING_FILE


try:
    from tools.vocab_tools.tag_obs_with_vocab_terms import tag_observation
    from tools.esgf_tools.add_drs_datasets import add_mapping
except ImportError:
    print('Oops. Looks like you have selected to write to MOLES '
          'but we cannot find the MOLES library')


def _tag_datasets():
    with open(MOLES_TAGS_FILE, 'rb') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',')
        for row in csvreader:
            tag_observation(row[0], row[1], 'clipc_skos_vocab')


def _tag_drs():
    with open(MOLES_ESGF_MAPPING_FILE, 'rb') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',')
        for row in csvreader:
            drs = row[1].split('.')
            add_mapping(row[0], drs[0], drs[1])


class CCITaggerCommandLineClientMoles(object):

    def parse_command_line(self, argv):
        parser = ArgumentParser(
            description='Update MOLES datasets. You can update tags or the DRS for datasets.'
            '\nThis uses the output files from moles_esgf_tag.',
            formatter_class=RawDescriptionHelpFormatter)

        parser.add_argument(
            '-d', '--drs', action='store_true',
            help=('update datasets in the MOLES catalogue with DRS.'))
        parser.add_argument(
            '-k', '--keywords', action='store_true',
            help=('update datasets in the MOLES catalogue with keywords.'))
        parser.add_argument(
            '-v', '--verbose', action='count',
            help='increase output verbosity',
            default=0)

        args = parser.parse_args(argv[1:])
        if args.drs is not None:
            if args.verbose >= 1:
                print("\n%s STARTED MOLES Update of DRS" %
                      (time.strftime("%H:%M:%S")))
            _tag_datasets()
        if args.keywords is not None:
            if args.verbose >= 1:
                print("\n%s STARTED MOLES Update of keywords" %
                      (time.strftime("%H:%M:%S")))
            _tag_datasets()

    @classmethod
    def main(cls, argv=sys.argv):
        start_time = datetime.now()
        client = cls()
        client.parse_command_line(argv)

        if args.verbose >= 1:
            print("%s FINISHED\n\n" % (time.strftime("%H:%M:%S")))
            end_time = datetime.now()
            time_diff = end_time - start_time
            hours, remainder = divmod(time_diff.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            print('Time taken %02d:%02d:%02d' % (hours, minutes, seconds))

        exit(0)


if __name__ == "__main__":
    CCITaggerCommandLineClientMoles.main()
