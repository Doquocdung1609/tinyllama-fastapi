"""Accounting concepts whose visible labels and standard iXBRL facts agree."""

# These rules are for the product verifier. Frozen research continues to use
# its versioned concept registry.
PRODUCT_ROWS = {
    'operating_cash': ('Lưu chuyển tiền thuần từ hoạt động kinh doanh', {
        'net cash from operations', 'net cash provided by operating activities',
        'net cash provided by (used in) operating activities', 'net cash used in operating activities',
        'net cash from operating activities'}, {'netcashprovidedbyusedinoperatingactivities'}),
    'investing_cash': ('Lưu chuyển tiền thuần từ hoạt động đầu tư', {
        'net cash from investing activities', 'net cash used in investing activities',
        'net cash provided by (used in) investing activities', 'net cash provided by investing activities'},
        {'netcashprovidedbyusedininvestingactivities'}),
    'financing_cash': ('Lưu chuyển tiền thuần từ hoạt động tài chính', {
        'net cash from financing activities', 'net cash used in financing activities',
        'net cash provided by (used in) financing activities', 'net cash provided by financing activities'},
        {'netcashprovidedbyusedinfinancingactivities'}),
    'operating_income': ('Lợi nhuận hoạt động', {'operating income','operating income (loss)','operating profit'},
        {'operatingincomeloss'}),
    'gross_profit': ('Lợi nhuận gộp', {'gross profit','gross margin'}, {'grossprofit'}),
    'cost_of_revenue': ('Giá vốn', {'cost of sales','cost of revenue','total cost of revenue'},
        {'costofrevenue','costofgoodsandservicessold','costofgoodssold'}),
    'current_assets': ('Tài sản ngắn hạn', {'total current assets','current assets'}, {'assetscurrent'}),
    'liabilities': ('Tổng nợ phải trả', {'total liabilities'}, {'liabilities'}),
    'current_liabilities': ('Nợ ngắn hạn', {'total current liabilities','current liabilities'}, {'liabilitiescurrent'}),
    'comprehensive_income': ('Thu nhập toàn diện', {'comprehensive income','total comprehensive income'},
        {'comprehensiveincomenetoftax','comprehensiveincomenetoftaxincludingportionattributabletononcontrollinginterest'}),
    'deferred_revenue': ('Doanh thu chưa thực hiện', {'deferred revenue','unearned revenue'},
        {'contractliabilitycurrent','deferredrevenuecurrent'}),
}


def concepts_for_label(label):
    return {'us-gaap:'+name for _, labels, names in PRODUCT_ROWS.values() if label in labels for name in names}
