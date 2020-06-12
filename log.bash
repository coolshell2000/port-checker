grep "% okay" private.ed/log/portchecker.py.log | awk '{$2=$3=$4=""; print $0}'

