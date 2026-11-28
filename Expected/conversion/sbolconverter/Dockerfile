# SynBioDex/SBOL-Converter image. Pinned to a specific release so the
# regenerated reference conversions are reproducible across contributor
# machines. This is the Java reference implementation of SBOL 2 <-> SBOL 3
# conversion; implementations compare their conversions against its output.
#
# Build: docker build -t sbolconverter-pinned Expected/conversion/sbolconverter/
# Used by: scripts/generate_expected.py --sbolconverter-image sbolconverter-pinned
#
# IMPORTANT — bump SBOLCONVERTER_TAG (and the jar filename below if the
# artifact version changes) when a new release ships. The release tag
# (1.0.4.1) and the jar's internal version (1.0.4-SNAPSHOT) differ, so both
# appear here. After bumping, re-run scripts/generate_expected.py with
# --sbolconverter-image and commit the resulting outputs.

# JDK base (not JRE) so `javac` is available for the Convert wrapper. JDK 21+
# is required: the release fat jar's classes are Java 21 bytecode (major 65).
# The image is only used locally by the generator script, so the size cost
# over a JRE-only multi-stage build is acceptable.
FROM eclipse-temurin:21-jdk AS runtime

ARG SBOLCONVERTER_TAG=1.0.4.1
ARG SBOLCONVERTER_JAR=sbol-converter-1.0.4-SNAPSHOT-jar-with-dependencies.jar
ARG SBOLCONVERTER_JAR_URL=https://github.com/SynBioDex/SBOL-Converter/releases/download/${SBOLCONVERTER_TAG}/${SBOLCONVERTER_JAR}

WORKDIR /opt/sbolconverter

# Fetch the pinned fat jar from the public GitHub release. (The Maven build
# pulls libSBOLj3 from GitHub Packages, which needs auth; the release fat jar
# avoids that entirely.)
ADD ${SBOLCONVERTER_JAR_URL} /opt/sbolconverter/sbol-converter.jar

COPY Convert.java /opt/sbolconverter/Convert.java
RUN javac -cp /opt/sbolconverter/sbol-converter.jar /opt/sbolconverter/Convert.java

ENTRYPOINT ["java", "-cp", "/opt/sbolconverter/sbol-converter.jar:/opt/sbolconverter", "Convert"]
