/**
 * with_packages — ebuild example using external packages (zlib).
 *
 * Demonstrates:
 *   - Declaring external package dependencies in build.yaml
 *   - Using zlib compression via the ebuild package manager
 *
 * Build with:
 *   cd examples/with_packages
 *   ebuild build
 */

#include <stdio.h>
#include <string.h>
#include <zlib.h>

int main(void) {
    printf("ebuild Package Manager Demo\n");
    printf("============================\n\n");

    printf("zlib version: %s\n\n", zlibVersion());

    const char *original = "Hello from ebuild with zlib compression! "
                           "This message will be compressed and decompressed.";
    uLong orig_len = (uLong)strlen(original) + 1;

    uLong comp_len = compressBound(orig_len);
    unsigned char compressed[1024];
    unsigned char decompressed[1024];

    int ret = compress(compressed, &comp_len,
                       (const unsigned char *)original, orig_len);
    if (ret != Z_OK) {
        fprintf(stderr, "Compression failed: %d\n", ret);
        return 1;
    }

    printf("Original size:    %lu bytes\n", (unsigned long)orig_len);
    printf("Compressed size:  %lu bytes\n", (unsigned long)comp_len);
    printf("Ratio:            %.1f%%\n",
           (1.0 - (double)comp_len / orig_len) * 100.0);

    uLong decomp_len = sizeof(decompressed);
    ret = uncompress(decompressed, &decomp_len, compressed, comp_len);
    if (ret != Z_OK) {
        fprintf(stderr, "Decompression failed: %d\n", ret);
        return 1;
    }

    printf("\nDecompressed: \"%s\"\n", (char *)decompressed);
    printf("Match: %s\n",
           strcmp(original, (char *)decompressed) == 0 ? "YES" : "NO");

    return 0;
}
