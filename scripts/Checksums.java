// Prints the Adler-32 and CRC-32C of each file named on the command line, as the Java
// runtime computes them (java.util.zip), for scripts/capture_program_output.py.
// Run with: java scripts/Checksums.java FILE...

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.zip.Adler32;
import java.util.zip.CRC32C;

public class Checksums {
    public static void main(String[] args) throws Exception {
        for (String name : args) {
            byte[] data = Files.readAllBytes(Path.of(name));
            Adler32 adler = new Adler32();
            adler.update(data);
            CRC32C crc = new CRC32C();
            crc.update(data);
            System.out.printf("%s %08x %08x%n", name, adler.getValue(), crc.getValue());
        }
    }
}
