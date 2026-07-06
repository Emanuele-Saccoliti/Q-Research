Attribute VB_Name = "RefreshDashboard"
Option Explicit

Public Sub RefreshBondCDSBasisDashboard()
    Application.ScreenUpdating = False
    Application.CalculateFull
    ThisWorkbook.RefreshAll
    Application.ScreenUpdating = True
    MsgBox "Bond-CDS basis dashboard refreshed.", vbInformation
End Sub
