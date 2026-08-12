param(
    [Parameter(Mandatory = $true)]
    [string]$Source,
    [Parameter(Mandatory = $true)]
    [string]$Output
)

$ErrorActionPreference = "Stop"

function Convert-Color($value) {
    if ($null -eq $value -or [long]$value -lt 0) { return $null }
    $number = [long]$value
    $red = $number -band 255
    $green = ($number -shr 8) -band 255
    $blue = ($number -shr 16) -band 255
    return "{0:X2}{1:X2}{2:X2}" -f $red, $green, $blue
}

function Release-Com($value) {
    if ($null -ne $value -and [Runtime.InteropServices.Marshal]::IsComObject($value)) {
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($value)
    }
}
function As-Double($value, [double]$default = 0) {
    if ($null -eq $value -or $value -is [DBNull]) { return $default }
    return [double]$value
}

function As-Int($value, [int]$default = 0) {
    if ($null -eq $value -or $value -is [DBNull]) { return $default }
    return [int]$value
}

function As-Bool($value, [bool]$default = $false) {
    if ($null -eq $value -or $value -is [DBNull]) { return $default }
    return [bool]$value
}

$excel = $null
$book = $null
$sheet = $null
try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $excel.AutomationSecurity = 3
    $book = $excel.Workbooks.Open($Source, 0, $true)
    $sheet = $book.Worksheets.Item(1)
    $used = $sheet.UsedRange

    $cells = @()
    for ($row = 1; $row -le $used.Rows.Count; $row++) {
        for ($column = 1; $column -le $used.Columns.Count; $column++) {
            $cell = $sheet.Cells.Item($row, $column)
            $font = $cell.Font
            $fill = $cell.Interior
            $protection = $cell.Protection
            $borderValues = @{}
            foreach ($edge in @(7, 8, 9, 10)) {
                $border = $cell.Borders.Item($edge)
                $borderValues[[string]$edge] = [ordered]@{
                    line_style = $border.LineStyle
                    weight = $border.Weight
                    color = Convert-Color $border.Color
                }
                Release-Com $border
            }
            $value = $cell.Value2
            $cells += [ordered]@{
                row = $row
                column = $column
                value = $value
                formula = $(if ($cell.HasFormula) { [string]$cell.Formula } else { $null })
                number_format = [string]$cell.NumberFormat
                font = [ordered]@{
                    name = [string]$font.Name
                    size = As-Double $font.Size 11
                    bold = As-Bool $font.Bold
                    italic = As-Bool $font.Italic
                    underline = As-Int $font.Underline -4142
                    strike = As-Bool $font.Strikethrough
                    color = Convert-Color $font.Color
                }
                fill = [ordered]@{
                    pattern = As-Int $fill.Pattern -4142
                    color = Convert-Color $fill.Color
                    pattern_color = Convert-Color $fill.PatternColor
                }
                alignment = [ordered]@{
                    horizontal = $cell.HorizontalAlignment
                    vertical = $cell.VerticalAlignment
                    wrap_text = As-Bool $cell.WrapText
                    shrink_to_fit = As-Bool $cell.ShrinkToFit
                    indent = As-Int $cell.IndentLevel
                    text_rotation = As-Int $cell.Orientation
                }
                borders = $borderValues
                protection = [ordered]@{
                    locked = As-Bool $protection.Locked $true
                    hidden = As-Bool $protection.FormulaHidden
                }
            }
            Release-Com $protection
            Release-Com $fill
            Release-Com $font
            Release-Com $cell
        }
    }

    $merges = @()
    $mergeSeen = @{}
    foreach ($item in $used.Cells) {
        if ([bool]$item.MergeCells) {
            $area = $item.MergeArea
            $address = $area.Address($false, $false)
            if (-not $mergeSeen.ContainsKey($address)) {
                $merges += $address
                $mergeSeen[$address] = $true
            }
            Release-Com $area
        }
        Release-Com $item
    }

    $columns = @()
    for ($column = 1; $column -le $used.Columns.Count; $column++) {
        $dimension = $sheet.Columns.Item($column)
        $columns += [ordered]@{
            column = $column
            width = [double]$dimension.ColumnWidth
            hidden = [bool]$dimension.Hidden
        }
        Release-Com $dimension
    }

    $rows = @()
    for ($row = 1; $row -le $used.Rows.Count; $row++) {
        $dimension = $sheet.Rows.Item($row)
        $rows += [ordered]@{
            row = $row
            height = [double]$dimension.RowHeight
            hidden = [bool]$dimension.Hidden
        }
        Release-Com $dimension
    }

    $page = $sheet.PageSetup
    $window = $excel.ActiveWindow
    $snapshot = [ordered]@{
        source_name = $book.Name
        source_format = [int]$book.FileFormat
        has_vba = [bool]$book.HasVBProject
        sheet_name = $sheet.Name
        used_range = $used.Address($false, $false)
        max_row = [int]$used.Rows.Count
        max_column = [int]$used.Columns.Count
        show_gridlines = [bool]$window.DisplayGridlines
        freeze_panes = [bool]$window.FreezePanes
        split_row = [int]$window.SplitRow
        split_column = [int]$window.SplitColumn
        zoom = [int]$window.Zoom
        shapes = [int]$sheet.Shapes.Count
        hyperlinks = [int]$sheet.Hyperlinks.Count
        conditional_formats = [int]$sheet.Cells.FormatConditions.Count
        merges = $merges
        columns = $columns
        rows = $rows
        cells = $cells
        page_setup = [ordered]@{
            orientation = [int]$page.Orientation
            paper_size = [int]$page.PaperSize
            zoom = $page.Zoom
            fit_to_pages_wide = $page.FitToPagesWide
            fit_to_pages_tall = $page.FitToPagesTall
            left_margin = [double]$page.LeftMargin
            right_margin = [double]$page.RightMargin
            top_margin = [double]$page.TopMargin
            bottom_margin = [double]$page.BottomMargin
            header_margin = [double]$page.HeaderMargin
            footer_margin = [double]$page.FooterMargin
            center_horizontally = [bool]$page.CenterHorizontally
            center_vertically = [bool]$page.CenterVertically
            print_area = [string]$page.PrintArea
            print_title_rows = [string]$page.PrintTitleRows
            print_title_columns = [string]$page.PrintTitleColumns
        }
    }
    $json = $snapshot | ConvertTo-Json -Depth 20
    $parent = Split-Path -Parent $Output
    if ($parent) { New-Item -ItemType Directory -Force $parent | Out-Null }
    [IO.File]::WriteAllText($Output, $json, [Text.UTF8Encoding]::new($false))
} finally {
    Release-Com $window
    Release-Com $page
    Release-Com $used
    Release-Com $sheet
    if ($book) { $book.Close($false) }
    Release-Com $book
    if ($excel) { $excel.Quit() }
    Release-Com $excel
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
