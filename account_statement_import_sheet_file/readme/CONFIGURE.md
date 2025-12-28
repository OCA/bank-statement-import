To create TXT/CSV/XLSX statement sheet columns mapping:

1.  Open *Invoicing \> Configuration \> Accounting \> Statement Sheet
    Mappings*
2.  Create mapping(s) according to your online banking software
    statement format


For PDF to CSV pre-processor, here is an example that may help you build one:

.. code-block:: python

    # Convert PDF Credit Card Statement to CSV file

    reader = data_file
    result = []

    summary = reader.pages[0].extract_text().split("\n")
    date = description = amount = None
    for idx, line in enumerate(summary):
        if not date:
            if line.endswith("Date"):
                date = summary[idx+1]
            continue
        if not description:
            if m := match(r"(Domiciliation.*) (\+[\d.,]+) €", line):
                description = m.group(1)
                amount = m.group(2)
                result.append(f"{date};{description};{amount}")
                break

    # header date format is day/month/year
    day,month,year = date.split("/")

    for page in reader.pages[1:]:
        lines = page.extract_text().split("\n")
        for idx, line in enumerate(lines):
            if not line.endswith("€"):
                line = line + " | " + lines[idx+1]
            m = match(r"([\d/]+) [\d/]+ (.+?) *([-+][\d.,]+) €", line)
            if m:
                # line date format is day/month
                # let's find out the year
                line_date = m.group(1)
                line_day, line_month = line_date.split("/")
                line_year = year if line_month <= month else str(int(year)-1)

                result.append(f"{line_date}/{line_year};{m.group(2)};{m.group(3)}")

    data_file = "\n".join(result).encode("utf-8")
