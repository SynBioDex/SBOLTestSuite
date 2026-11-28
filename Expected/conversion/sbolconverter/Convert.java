// Reference SBOL-Converter wrapper for cross-implementation comparisons.
// Drives one conversion and writes the result to stdout so the caller owns all
// equivalence checking.
//
// Usage: Convert <inputFile> <to-sbol3|to-sbol2> <format>
//   to-sbol3: read SBOL 2, convert, write SBOL 3 in <format> (ttl|rdf|jsonld|nt)
//   to-sbol2: read SBOL 3, convert, write SBOL 2 RDF/XML (<format> ignored)
//
// Save-time validation is disabled: the reference otherwise refuses to emit
// output it deems invalid, but the differential test needs the raw conversion.
import java.io.ByteArrayInputStream;
import java.io.File;
import java.nio.file.Files;
import org.sbolstandard.core2.SBOLReader;
import org.sbolstandard.core2.SBOLWriter;
import org.sbolstandard.core3.io.SBOLFormat;
import org.sbolstandard.core3.io.SBOLIO;
import org.sbolstandard.core3.util.Configuration;

public class Convert {
    public static void main(String[] args) throws Exception {
        Configuration.getInstance().setValidateBeforeSaving(false);
        Configuration.getInstance().setValidateAfterSettingProperties(false);
        Configuration.getInstance().setValidateAfterReadingSBOLDocuments(false);
        SBOLReader.setKeepGoing(true);
        SBOLWriter.setKeepGoing(true);

        String input = args[0];
        String direction = args[1];
        String format = args.length > 2 ? args[2] : "nt";

        if (direction.equals("to-sbol3")) {
            byte[] bytes = Files.readAllBytes(new File(input).toPath());
            org.sbolstandard.core2.SBOLDocument doc =
                SBOLReader.read(new ByteArrayInputStream(bytes));
            var sbol3 = new org.sbolstandard.converter.sbol23_31.SBOLDocumentConverter().convert(doc);
            System.out.print(SBOLIO.write(sbol3, format(format)));
        } else if (direction.equals("to-sbol2")) {
            org.sbolstandard.core3.entity.SBOLDocument sbol3 = SBOLIO.read(new File(input));
            org.sbolstandard.core2.SBOLDocument sbol2 =
                new org.sbolstandard.converter.sbol31_23.SBOLDocumentConverter().convert(sbol3);
            SBOLWriter.write(sbol2, System.out);
        } else {
            throw new IllegalArgumentException("direction: " + direction);
        }
    }

    static SBOLFormat format(String n) {
        switch (n) {
            case "ttl": case "turtle": return SBOLFormat.TURTLE;
            case "rdf": case "rdfxml": return SBOLFormat.RDFXML;
            case "jsonld": return SBOLFormat.JSONLD;
            case "nt": case "ntriples": return SBOLFormat.NTRIPLES;
            default: throw new IllegalArgumentException("format: " + n);
        }
    }
}
