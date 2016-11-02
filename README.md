# CCI Tagger

## Overview

This package provides a command line tool moles_esgf_tag to generate dataset
tags for both MOLES and ESGF.

## Installation

Create a Python virtual environment:

```bash
virtualenv tagger
source tagger/bin/activate
```

Find the [latest release of the code](https://github.com/cedadev/cci-tagger/releases) and install it in the virtual environment, i.e. for version 1.0.0:

```bash
pip install https://github.com/cedadev/cci-tagger/archive/v1.0.0.tar.gz
```

## Usage

```
moles_esgf_tag [-h] (-f FILE | -d DATASET | -s) [--file_count FILE_COUNT] [--no_check_sum] [-v]
```

You can tag an individual dataset, or tag all the datasets listed in a file. By default a check sum will be produces for each file.

Arguments:

    -h, --help            show help message and exit

    -f FILE, --file FILE  the name of the file containing a list of datasets to process. This option is used for
                          tagging one or more datasets.

    -d DATASET, --dataset DATASET
                          the full path to the dataset that is to be tagged. This option is used to tag a single
                          dataset.

    -s, --show_mappings   show the local vocabulary mappings

    -m, --use_mappings    use the local vocabulary mappings. This will map a number of non compliant terms to
                          allowed terms.

    --file_count FILE_COUNT
                          how many .nt files to look at per dataset

    --no_check_sum        do not produce a check sum for each file

    -v, --verbose         increase output verbosity


# Output

A number of files are produced as output:
*  __esgf_drs.json__ contains a list of DRS and associated files and check sums
*  __moles_tags.csv__ contains a list of dataset paths and vocabulary URLs
*  __moles_esgf_mapping.csv__ contains mappings between dataset paths and DRS
*  __error.txt__ contains a list of errors

# Examples

```bash
moles_esgf_tag -d /neodc/esacci/cloud/data/L3C/avhrr_noaa-16 -v
moles_esgf_tag -f datapath --file_count 2 --no_check_sum -m -v
moles_esgf_tag -s
```

