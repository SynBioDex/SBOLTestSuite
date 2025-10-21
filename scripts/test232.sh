#!/bin/bash
# Usage: <path to Python sbol-converter> <path to Python sbol-diff> <path to Java Jar for sbol-converter> <path to SBOL2 tests>

NUMFILES=0
JAVASCORE=0
PYTHONSCORE=0

if [ -d "$4" ]; then
    for file in "$4"/*; do
      if [ -f "$file" ]; then
        echo "File: $file"
        NUMFILES=$((NUMFILES+1))

        echo "Using Python to convert SBOL2 to SBOL3"
        $1 --force-new-converter SBOL2 SBOL3 "$file" -o python23.nt
        echo "Using Python to convert SBOL3 to SBOL2"
        $1 --force-new-converter SBOL3 SBOL2 python23.nt -o python32.xml 
        echo "Comparing original SBOL2 to converted SBOL2 using Python"
        $2 --strip-backport-properties "$file" python32.xml
        if [ $? -eq 0 ]; then
            PYTHONSCORE=$((PYTHONSCORE+1))
            echo "Python conversion matches for $file"
        else
            echo "Python conversion DOES NOT match for $file"
        fi

        echo "Using Java to convert SBOL2 to SBOL3"
        java -jar $3 -l SBOL3 "$file" -o java23.xml
        echo "Using Java to convert SBOL3 to SBOL2"
        java -jar $3 -l SBOL2 java23.xml -o java32.xml
        echo "Comparing original SBOL2 to converted SBOL2 using Java"
        java -jar $3 -no "$file" -e java32.xml
        if [ $? -eq 0 ]; then
            JAVASCORE=$((JAVASCORE+1))
            echo "Java conversion matches for $file"
        else
            echo "Java conversion DOES NOT match for $file"
        fi
      fi
      echo "Python Score = $PYTHONSCORE"
      echo "Java Score = $JAVASCORE"
      echo "Number of Files = $NUMFILES"
    done
elif [ -f "$4" ]; then
    echo "File: $4"
    echo "Using Python to convert SBOL2 to SBOL3"
    $1 --force-new-converter SBOL2 SBOL3 "$4" -o python23.nt
    echo "Using Python to convert SBOL3 to SBOL2"
    $1 --force-new-converter SBOL3 SBOL2 python23.nt -o python32.xml 
    echo "Comparing original SBOL2 to converted SBOL2 using Python"
    $2 --strip-backport-properties "$4" python32.xml
    if [ $? -eq 0 ]; then
        echo "Python conversion matches for $4"
    else
        echo "Python conversion DOES NOT match for $4"
    fi
 
    echo "Using Java to convert SBOL2 to SBOL3"
    java -jar $3 -l SBOL3 "$4" -o java23.xml
    echo "Using Java to convert SBOL3 to SBOL2"
    java -jar $3 -l SBOL2 java23.xml -o java32.xml
    echo "Comparing original SBOL2 to converted SBOL2 using Java"
    java -jar $3 -no "$4" -e java32.xml
    if [ $? -eq 0 ]; then
        echo "Java conversion matches for $4"
    else
        echo "Java conversion DOES NOT match for $4"
    fi
else
  echo "Error: '$4' not found."
  exit 1
fi
