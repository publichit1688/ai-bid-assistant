param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("microsoft_word", "wps")]
    [string]$Engine,

    [Parameter(Mandatory = $true)]
    [string]$SourcePath,

    [Parameter(Mandatory = $true)]
    [string]$TargetPath
)

$ErrorActionPreference = "Stop"
$application = $null
$document = $null

try {
    if ($Engine -eq "microsoft_word") {
        $application = New-Object -ComObject "Word.Application"
    }
    else {
        foreach ($programmaticId in @("kwps.Application", "wps.Application")) {
            try {
                $application = New-Object -ComObject $programmaticId
                break
            }
            catch {
                $application = $null
            }
        }
        if ($null -eq $application) {
            throw "WPS automation is unavailable"
        }
    }

    $application.Visible = $false
    try { $application.DisplayAlerts = 0 } catch {}
    $document = $application.Documents.Open($SourcePath, $false, $true)

    try {
        $document.ExportAsFixedFormat($TargetPath, 17)
    }
    catch {
        $document.SaveAs($TargetPath, 17)
    }
}
finally {
    if ($null -ne $document) {
        try { $document.Close($false) } catch {}
        try { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($document) } catch {}
    }
    if ($null -ne $application) {
        try { $application.Quit() } catch {}
        try { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($application) } catch {}
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

if (-not (Test-Path -LiteralPath $TargetPath)) {
    throw "PDF output was not created"
}
