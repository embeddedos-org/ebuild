// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/* epdf.c - ePdf: Lightweight PDF reader and signature tool */
#include "eosuite.h"
#include "platform.h"

static void trim_nl(char *s) {
    size_t len = strlen(s);
    if (len > 0 && s[len - 1] == '\n') s[len - 1] = '\0';
}

static void pdf_view(void) {
    char input[MAX_INPUT_LEN];
    char filepath[MAX_PATH_LEN];
    char cmd[MAX_PATH_LEN * 3];

    printf("\n  Enter PDF file path: ");
    fflush(stdout);
    if (fgets(filepath, sizeof(filepath), stdin) == NULL) return;
    trim_nl(filepath);
    if (strlen(filepath) == 0) return;

    printf("\n  View mode:\n");
    printf("   1. Text extraction (read in terminal)\n");
    printf("   2. Open in system PDF viewer\n");
    printf("  Select [1]: ");
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;

    if (atoi(input) == 2) {
#ifdef _WIN32
        snprintf(cmd, sizeof(cmd), "start \"\" \"%s\"", filepath);
#elif defined(__APPLE__)
        snprintf(cmd, sizeof(cmd), "open '%s'", filepath);
#else
        snprintf(cmd, sizeof(cmd), "xdg-open '%s' 2>/dev/null &", filepath);
#endif
        system(cmd);
        printf("  Opened in system viewer.\n");
        printf("  Press Enter...\n");
        fgets(input, sizeof(input), stdin);
        return;
    }

    /* Extract text from PDF */
    CLEAR_SCREEN();
    term_set_color(COLOR_CYAN, COLOR_BLACK);
    printf("  PDF: %s\n", filepath);
    printf("  ========================================\n\n");
    term_reset_color();

#ifdef _WIN32
    /* Try pdftotext (poppler), then mutool, then PowerShell */
    snprintf(cmd, sizeof(cmd),
        "where pdftotext >nul 2>nul && (pdftotext -layout \"%s\" - 2>nul) || "
        "where mutool >nul 2>nul && (mutool draw -F text \"%s\" 2>nul) || "
        "powershell -NoProfile -Command \""
        "Add-Type -Path 'C:\\Windows\\Microsoft.NET\\assembly\\GAC_MSIL\\*\\*\\System.Windows.Forms.dll' -ErrorAction SilentlyContinue;"
        "try{"
        "[Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null;"
        "Write-Host '  [PDF text extraction requires pdftotext or mutool]';"
        "Write-Host '  Install poppler-utils: winget install poppler';"
        "Write-Host '  Or install MuPDF: https://mupdf.com'"
        "}catch{Write-Host '  Cannot extract text'}\"",
        filepath, filepath);
#else
    snprintf(cmd, sizeof(cmd),
        "command -v pdftotext >/dev/null 2>&1 && pdftotext -layout '%s' - 2>/dev/null || "
        "command -v mutool >/dev/null 2>&1 && mutool draw -F text '%s' 2>/dev/null || "
        "command -v pdf2txt >/dev/null 2>&1 && pdf2txt '%s' 2>/dev/null || "
        "echo '  Install poppler-utils: sudo apt install poppler-utils'",
        filepath, filepath, filepath);
#endif

    system(cmd);

    printf("\n\n  Press Enter to continue...\n");
    fgets(input, sizeof(input), stdin);
}

static void pdf_info(void) {
    char input[MAX_INPUT_LEN];
    char filepath[MAX_PATH_LEN];
    char cmd[MAX_PATH_LEN * 3];

    printf("\n  Enter PDF file path: ");
    fflush(stdout);
    if (fgets(filepath, sizeof(filepath), stdin) == NULL) return;
    trim_nl(filepath);
    if (strlen(filepath) == 0) return;

    term_set_color(COLOR_CYAN, COLOR_BLACK);
    printf("\n  PDF Information: %s\n", filepath);
    printf("  ========================================\n");
    term_reset_color();

#ifdef _WIN32
    snprintf(cmd, sizeof(cmd),
        "where pdfinfo >nul 2>nul && (pdfinfo \"%s\" 2>nul) || "
        "where mutool >nul 2>nul && (mutool info \"%s\" 2>nul) || "
        "powershell -NoProfile -Command \""
        "$f=Get-Item '%s' -ErrorAction SilentlyContinue;"
        "if($f){"
        "Write-Host ('  File: ' + $f.Name);"
        "Write-Host ('  Size: ' + [math]::Round($f.Length/1KB,2) + ' KB');"
        "Write-Host ('  Modified: ' + $f.LastWriteTime);"
        "$r=[IO.File]::OpenRead($f.FullName);"
        "$b=New-Object byte[] 1024;$r.Read($b,0,1024)|Out-Null;$r.Close();"
        "$h=[Text.Encoding]::ASCII.GetString($b);"
        "if($h -match '/Pages\\s+(\\d+)'){Write-Host ('  Pages: ~' + $Matches[1])};"
        "if($h -match '/Title\\s*\\(([^)]+)\\)'){Write-Host ('  Title: ' + $Matches[1])};"
        "if($h -match '/Author\\s*\\(([^)]+)\\)'){Write-Host ('  Author: ' + $Matches[1])}"
        "}else{Write-Host '  File not found'}\"",
        filepath, filepath, filepath);
#else
    snprintf(cmd, sizeof(cmd),
        "command -v pdfinfo >/dev/null 2>&1 && pdfinfo '%s' 2>/dev/null || "
        "command -v mutool >/dev/null 2>&1 && mutool info '%s' 2>/dev/null || "
        "command -v exiftool >/dev/null 2>&1 && exiftool '%s' 2>/dev/null || "
        "{ echo '  File: %s'; ls -lh '%s' 2>/dev/null | awk '{print \"  Size: \"$5}'; "
        "echo '  Install poppler-utils for full PDF info'; }",
        filepath, filepath, filepath, filepath, filepath);
#endif

    system(cmd);

    printf("\n  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void pdf_sign(void) {
    char input[MAX_INPUT_LEN];
    char filepath[MAX_PATH_LEN];
    char output[MAX_PATH_LEN];
    char sig_text[MAX_INPUT_LEN];
    char cmd[MAX_PATH_LEN * 4];

    printf("\n  PDF Digital Signature\n");
    printf("  ========================================\n\n");

    printf("  Input PDF: ");
    fflush(stdout);
    if (fgets(filepath, sizeof(filepath), stdin) == NULL) return;
    trim_nl(filepath);
    if (strlen(filepath) == 0) return;

    printf("\n  Signature type:\n");
    printf("   1. Text stamp (name, date, notes)\n");
    printf("   2. Image signature (from file)\n");
    printf("   3. Certificate-based (requires OpenSSL)\n");
    printf("  Select [1]: ");
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;
    int sig_type = atoi(input);
    if (sig_type < 1 || sig_type > 3) sig_type = 1;

    /* Build output filename */
    strncpy(output, filepath, MAX_PATH_LEN - 20);
    char *dot = strrchr(output, '.');
    if (dot) *dot = '\0';
    strcat(output, "_signed.pdf");

    switch (sig_type) {
    case 1: { /* Text stamp */
        printf("  Signature text (name): ");
        fflush(stdout);
        if (fgets(sig_text, sizeof(sig_text), stdin) == NULL) return;
        trim_nl(sig_text);
        if (strlen(sig_text) == 0) strcpy(sig_text, "Signed");

        char date_str[64];
        time_t now = time(NULL);
        struct tm *t = localtime(&now);
        strftime(date_str, sizeof(date_str), "%Y-%m-%d %H:%M", t);

        printf("  Page number (0=all, default=last): ");
        fflush(stdout);
        if (fgets(input, sizeof(input), stdin) == NULL) return;
        int page = atoi(input);

        term_set_color(COLOR_YELLOW, COLOR_BLACK);
        printf("\n  Applying text signature...\n");
        term_reset_color();

#ifdef _WIN32
        /* Try pdftk stamp, or cpdf, or qpdf */
        snprintf(cmd, sizeof(cmd),
            "where pdftk >nul 2>nul && ("
            "echo \"Signed by: %s\" > \"%%TEMP%%\\sig.txt\" && "
            "echo \"Date: %s\" >> \"%%TEMP%%\\sig.txt\" && "
            "pdftk \"%s\" stamp \"%%TEMP%%\\sig.txt\" output \"%s\" 2>nul && "
            "echo   Signed: %s"
            ") || ("
            "copy \"%s\" \"%s\" >nul 2>nul && "
            "echo   [Copied PDF - install pdftk for true stamping] && "
            "echo   Signature: %s && "
            "echo   Date: %s && "
            "echo   Output: %s"
            ")",
            sig_text, date_str, filepath, output, output,
            filepath, output, sig_text, date_str, output);
#else
        snprintf(cmd, sizeof(cmd),
            "command -v pdftk >/dev/null 2>&1 && {"
            "echo 'Signed by: %s' > /tmp/sig.txt && "
            "echo 'Date: %s' >> /tmp/sig.txt && "
            "pdftk '%s' stamp /tmp/sig.txt output '%s' 2>/dev/null && "
            "echo '  Signed: %s'; "
            "} || command -v cpdf >/dev/null 2>&1 && {"
            "cpdf -add-text 'Signed: %s - %s' -bottomright 50 '%s' -o '%s' 2>/dev/null && "
            "echo '  Signed: %s'; "
            "} || {"
            "cp '%s' '%s' && "
            "echo '  [Copied PDF - install pdftk or cpdf for true stamping]' && "
            "echo '  Signature: %s' && echo '  Date: %s' && echo '  Output: %s'; }",
            sig_text, date_str, filepath, output, output,
            sig_text, date_str, filepath, output, output,
            filepath, output, sig_text, date_str, output);
#endif
        system(cmd);
        break;
    }

    case 2: { /* Image signature */
        char img_path[MAX_PATH_LEN];
        printf("  Signature image file (PNG/JPG): ");
        fflush(stdout);
        if (fgets(img_path, sizeof(img_path), stdin) == NULL) return;
        trim_nl(img_path);
        if (strlen(img_path) == 0) return;

        printf("  Page number (default=1): ");
        fflush(stdout);
        if (fgets(input, sizeof(input), stdin) == NULL) return;
        int page = atoi(input);
        if (page <= 0) page = 1;

        term_set_color(COLOR_YELLOW, COLOR_BLACK);
        printf("\n  Applying image signature...\n");
        term_reset_color();

#ifdef _WIN32
        snprintf(cmd, sizeof(cmd),
            "where pdftk >nul 2>nul && ("
            "pdftk \"%s\" stamp \"%s\" output \"%s\" 2>nul && echo   Signed: %s"
            ") || (echo   Install pdftk for image stamping: https://www.pdflabs.com/tools/pdftk-the-pdf-toolkit/)",
            filepath, img_path, output, output);
#else
        snprintf(cmd, sizeof(cmd),
            "command -v pdftk >/dev/null 2>&1 && "
            "pdftk '%s' stamp '%s' output '%s' 2>/dev/null && echo '  Signed: %s' || "
            "echo '  Install pdftk: sudo apt install pdftk'",
            filepath, img_path, output, output);
#endif
        system(cmd);
        break;
    }

    case 3: { /* Certificate-based */
        char cert_path[MAX_PATH_LEN];
        char key_path[MAX_PATH_LEN];

        printf("  Certificate file (.pem/.crt): ");
        fflush(stdout);
        if (fgets(cert_path, sizeof(cert_path), stdin) == NULL) return;
        trim_nl(cert_path);

        printf("  Private key file (.pem/.key): ");
        fflush(stdout);
        if (fgets(key_path, sizeof(key_path), stdin) == NULL) return;
        trim_nl(key_path);

        term_set_color(COLOR_YELLOW, COLOR_BLACK);
        printf("\n  Applying certificate signature...\n");
        term_reset_color();

#ifdef _WIN32
        snprintf(cmd, sizeof(cmd),
            "where openssl >nul 2>nul && ("
            "openssl smime -sign -in \"%s\" -out \"%s\" -signer \"%s\" -inkey \"%s\" -outform PEM 2>nul && "
            "echo   Signed with certificate: %s"
            ") || (echo   OpenSSL not found. Install from https://slproweb.com/products/Win32OpenSSL.html)",
            filepath, output, cert_path, key_path, output);
#else
        snprintf(cmd, sizeof(cmd),
            "command -v openssl >/dev/null 2>&1 && "
            "openssl smime -sign -in '%s' -out '%s' -signer '%s' -inkey '%s' -outform PEM 2>/dev/null && "
            "echo '  Signed with certificate: %s' || "
            "echo '  OpenSSL not found. Install: sudo apt install openssl'",
            filepath, output, cert_path, key_path, output);
#endif
        system(cmd);
        break;
    }
    }

    printf("\n  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void pdf_merge(void) {
    char input[MAX_INPUT_LEN];
    char files[MAX_PATH_LEN * 4];
    char output[MAX_PATH_LEN];
    char cmd[MAX_PATH_LEN * 6];

    printf("\n  Merge Multiple PDFs\n");
    printf("  ========================================\n\n");

    printf("  Input PDF files (space-separated): ");
    fflush(stdout);
    if (fgets(files, sizeof(files), stdin) == NULL) return;
    trim_nl(files);
    if (strlen(files) == 0) return;

    printf("  Output file [merged.pdf]: ");
    fflush(stdout);
    if (fgets(output, sizeof(output), stdin) == NULL) return;
    trim_nl(output);
    if (strlen(output) == 0) strcpy(output, "merged.pdf");

    term_set_color(COLOR_YELLOW, COLOR_BLACK);
    printf("\n  Merging...\n");
    term_reset_color();

#ifdef _WIN32
    snprintf(cmd, sizeof(cmd),
        "where pdftk >nul 2>nul && (pdftk %s cat output \"%s\" 2>nul && echo   Merged: %s) || "
        "where qpdf >nul 2>nul && (qpdf --empty --pages %s -- \"%s\" 2>nul && echo   Merged: %s) || "
        "(echo   Install pdftk or qpdf for PDF merging)",
        files, output, output, files, output, output);
#else
    snprintf(cmd, sizeof(cmd),
        "command -v pdftk >/dev/null 2>&1 && pdftk %s cat output '%s' 2>/dev/null && echo '  Merged: %s' || "
        "command -v qpdf >/dev/null 2>&1 && qpdf --empty --pages %s -- '%s' 2>/dev/null && echo '  Merged: %s' || "
        "command -v pdfunite >/dev/null 2>&1 && pdfunite %s '%s' 2>/dev/null && echo '  Merged: %s' || "
        "echo '  Install pdftk, qpdf, or poppler-utils'",
        files, output, output, files, output, output, files, output, output);
#endif

    system(cmd);

    printf("\n  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void pdf_split(void) {
    char input[MAX_INPUT_LEN];
    char filepath[MAX_PATH_LEN];
    char cmd[MAX_PATH_LEN * 3];

    printf("\n  Split PDF into Pages\n");
    printf("  ========================================\n\n");

    printf("  Input PDF: ");
    fflush(stdout);
    if (fgets(filepath, sizeof(filepath), stdin) == NULL) return;
    trim_nl(filepath);
    if (strlen(filepath) == 0) return;

    printf("\n  1. Split ALL pages (one file per page)\n");
    printf("  2. Extract specific pages (e.g. 1-3,5,7)\n");
    printf("  Select [1]: ");
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;

    term_set_color(COLOR_YELLOW, COLOR_BLACK);
    printf("\n  Splitting...\n");
    term_reset_color();

    if (atoi(input) == 2) {
        char pages[128];
        char output[MAX_PATH_LEN];
        printf("  Pages (e.g. 1-3 or 5): ");
        fflush(stdout);
        if (fgets(pages, sizeof(pages), stdin) == NULL) return;
        trim_nl(pages);

        strncpy(output, filepath, MAX_PATH_LEN - 20);
        char *dot = strrchr(output, '.');
        if (dot) *dot = '\0';
        strcat(output, "_extract.pdf");

#ifdef _WIN32
        snprintf(cmd, sizeof(cmd),
            "where pdftk >nul 2>nul && (pdftk \"%s\" cat %s output \"%s\" 2>nul && echo   Extracted: %s) || "
            "where qpdf >nul 2>nul && (qpdf \"%s\" --pages . %s -- \"%s\" 2>nul && echo   Extracted: %s) || "
            "(echo   Install pdftk or qpdf)",
            filepath, pages, output, output, filepath, pages, output, output);
#else
        snprintf(cmd, sizeof(cmd),
            "command -v pdftk >/dev/null 2>&1 && pdftk '%s' cat %s output '%s' && echo '  Extracted: %s' || "
            "command -v qpdf >/dev/null 2>&1 && qpdf '%s' --pages . %s -- '%s' && echo '  Extracted: %s' || "
            "echo '  Install pdftk or qpdf'",
            filepath, pages, output, output, filepath, pages, output, output);
#endif
        system(cmd);
    } else {
#ifdef _WIN32
        snprintf(cmd, sizeof(cmd),
            "where pdftk >nul 2>nul && (pdftk \"%s\" burst 2>nul && echo   Split into individual pages) || "
            "(echo   Install pdftk for page splitting)",
            filepath);
#else
        snprintf(cmd, sizeof(cmd),
            "command -v pdftk >/dev/null 2>&1 && pdftk '%s' burst 2>/dev/null && echo '  Split into individual pages' || "
            "command -v pdfseparate >/dev/null 2>&1 && pdfseparate '%s' 'page_%%d.pdf' 2>/dev/null && echo '  Split complete' || "
            "echo '  Install pdftk or poppler-utils'",
            filepath, filepath);
#endif
        system(cmd);
    }

    printf("\n  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

static void pdf_convert(void) {
    char input[MAX_INPUT_LEN];
    char filepath[MAX_PATH_LEN];
    char cmd[MAX_PATH_LEN * 3];

    printf("\n  PDF Conversion\n");
    printf("  ========================================\n\n");

    printf("  Input PDF: ");
    fflush(stdout);
    if (fgets(filepath, sizeof(filepath), stdin) == NULL) return;
    trim_nl(filepath);
    if (strlen(filepath) == 0) return;

    char output[MAX_PATH_LEN];
    strncpy(output, filepath, MAX_PATH_LEN - 20);
    char *dot = strrchr(output, '.');
    if (dot) *dot = '\0';

    printf("\n  Convert to:\n");
    printf("   1. Text (.txt)\n");
    printf("   2. Images (.png per page)\n");
    printf("   3. HTML\n");
    printf("   4. Word (.docx)\n");
    printf("  Select: ");
    fflush(stdout);
    if (fgets(input, sizeof(input), stdin) == NULL) return;

    term_set_color(COLOR_YELLOW, COLOR_BLACK);
    printf("\n  Converting...\n");
    term_reset_color();

    switch (atoi(input)) {
    case 1: { /* PDF -> TXT */
        char out_txt[MAX_PATH_LEN];
        snprintf(out_txt, sizeof(out_txt), "%s.txt", output);
#ifdef _WIN32
        snprintf(cmd, sizeof(cmd),
            "where pdftotext >nul 2>nul && (pdftotext -layout \"%s\" \"%s\" 2>nul && echo   Converted: %s) || "
            "(echo   Install poppler-utils)", filepath, out_txt, out_txt);
#else
        snprintf(cmd, sizeof(cmd),
            "pdftotext -layout '%s' '%s' 2>/dev/null && echo '  Converted: %s' || echo '  Install poppler-utils'",
            filepath, out_txt, out_txt);
#endif
        system(cmd);
        break;
    }
    case 2: { /* PDF -> PNG */
#ifdef _WIN32
        snprintf(cmd, sizeof(cmd),
            "where pdftoppm >nul 2>nul && (pdftoppm -png \"%s\" \"%s\" 2>nul && echo   Converted to PNG images) || "
            "where mutool >nul 2>nul && (mutool draw -o \"%s_%%d.png\" \"%s\" 2>nul && echo   Converted) || "
            "where magick >nul 2>nul && (magick convert -density 200 \"%s\" \"%s_%%03d.png\" 2>nul && echo   Converted) || "
            "(echo   Install poppler-utils, MuPDF, or ImageMagick)",
            filepath, output, output, filepath, filepath, output);
#else
        snprintf(cmd, sizeof(cmd),
            "command -v pdftoppm >/dev/null 2>&1 && pdftoppm -png '%s' '%s' && echo '  Converted to PNG' || "
            "command -v mutool >/dev/null 2>&1 && mutool draw -o '%s_%%d.png' '%s' && echo '  Converted' || "
            "echo '  Install poppler-utils or MuPDF'",
            filepath, output, output, filepath);
#endif
        system(cmd);
        break;
    }
    case 3: { /* PDF -> HTML */
        char out_html[MAX_PATH_LEN];
        snprintf(out_html, sizeof(out_html), "%s.html", output);
#ifdef _WIN32
        snprintf(cmd, sizeof(cmd),
            "where pdftohtml >nul 2>nul && (pdftohtml -s \"%s\" \"%s\" 2>nul && echo   Converted: %s) || "
            "(echo   Install poppler-utils)", filepath, out_html, out_html);
#else
        snprintf(cmd, sizeof(cmd),
            "command -v pdftohtml >/dev/null 2>&1 && pdftohtml -s '%s' '%s' && echo '  Converted: %s' || "
            "echo '  Install poppler-utils'", filepath, out_html, out_html);
#endif
        system(cmd);
        break;
    }
    case 4: { /* PDF -> DOCX */
        char out_docx[MAX_PATH_LEN];
        snprintf(out_docx, sizeof(out_docx), "%s.docx", output);
#ifdef _WIN32
        snprintf(cmd, sizeof(cmd),
            "where pandoc >nul 2>nul && (pandoc \"%s\" -o \"%s\" 2>nul && echo   Converted: %s) || "
            "where soffice >nul 2>nul && (soffice --headless --convert-to docx \"%s\" 2>nul && echo   Converted) || "
            "(echo   Install pandoc or LibreOffice)", filepath, out_docx, out_docx, filepath);
#else
        snprintf(cmd, sizeof(cmd),
            "command -v pandoc >/dev/null 2>&1 && pandoc '%s' -o '%s' && echo '  Converted: %s' || "
            "command -v soffice >/dev/null 2>&1 && soffice --headless --convert-to docx '%s' && echo '  Converted' || "
            "echo '  Install pandoc or LibreOffice'", filepath, out_docx, out_docx, filepath);
#endif
        system(cmd);
        break;
    }
    }

    printf("\n  Press Enter...\n");
    fgets(input, sizeof(input), stdin);
}

void run_epdf(void) {
    char input[MAX_INPUT_LEN];

    while (1) {
        CLEAR_SCREEN();
        term_set_color(COLOR_CYAN, COLOR_BLACK);
        printf("  +========================================+\n");
        printf("  |     ePdf - PDF Reader & Signature      |\n");
        printf("  +========================================+\n");
        term_reset_color();

        printf("\n  Read, sign, merge, split, convert PDFs.\n\n");
        printf("   1. View / Read PDF\n");
        printf("   2. PDF Info (metadata)\n");
        printf("   3. Sign PDF (text/image/certificate)\n");
        printf("   4. Merge PDFs\n");
        printf("   5. Split / Extract Pages\n");
        printf("   6. Convert PDF (txt/png/html/docx)\n");
        printf("   0. Back to Menu\n");
        printf("\n  Select: ");
        fflush(stdout);

        if (fgets(input, sizeof(input), stdin) == NULL) return;

        CLEAR_SCREEN();
        switch (atoi(input)) {
        case 1: pdf_view();    break;
        case 2: pdf_info();    break;
        case 3: pdf_sign();    break;
        case 4: pdf_merge();   break;
        case 5: pdf_split();   break;
        case 6: pdf_convert(); break;
        case 0: return;
        }
    }
}
