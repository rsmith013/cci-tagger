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
import ConfigParser


# Name of fake section to create
SECTION_NAME = 'asection'


class _FakeSecHead(object):
    """
    Create a fake header for the properties file so we can use ConfigParser.

    """

    def __init__(self, file_path):
        self.file_path = file_path
        self.sechead = '[{}]\n'.format(SECTION_NAME)

    def readline(self):
        if self.sechead:
            try:
                return self.sechead
            finally:
                self.sechead = None
        else:
            return self.file_path.readline()


class Properties(object):
    """
    Parse the properties file.

    """

    def __init__(self, file_path):
        """
        Set up the parser using a fake section head.

        @param file_path(str): the name and path of the properties file.

        """
        self.cp = ConfigParser.SafeConfigParser()
        self.cp.readfp(_FakeSecHead(open(file_path)))

    def properties(self):
        """
        Get the properties as a dictionary.

        @return a dict where:
                key = property name
                value = property value
        """
        props = {}
        for option in self.cp.options(SECTION_NAME):
            props[option] = self.cp.get(SECTION_NAME, option)
        return props
