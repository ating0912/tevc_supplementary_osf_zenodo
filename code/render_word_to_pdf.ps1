param(
    [Parameter(Mandatory = $true)][string]$InputDocx,
    [Parameter(Mandatory = $true)][string]$OutputPdf
)

$ErrorActionPreference = 'Stop'
$word = $null
$doc = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.AutomationSecurity = 3
    $doc = $word.Documents.OpenNoRepairDialog($InputDocx, $false, $true)
    $doc.ExportAsFixedFormat($OutputPdf, 17, $false, 0, 0, 1, 9999, 0, $true, $true, 0, $true, $true, $false)
    $doc.Close($false)
    $doc = $null
    Write-Output $OutputPdf
}
finally {
    if ($null -ne $doc) {
        $doc.Close($false)
    }
    if ($null -ne $word) {
        $word.Quit()
    }
}
