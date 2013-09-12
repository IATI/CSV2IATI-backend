activity_order = [
'reporting-org',
'iati-identifier',
'other-identifier',
'activity-website',
'title',
'description',
'activity-status',
'activity-date',
'contact-info',
'participating-org',
'activity-scope',
'recipient-country',
'recipient-region',
'location',
'sector',
'country-budget-items',
'policy-marker',
'collaboration-type',
'default-finance-type',
'default-flow-type',
'default-aid-type',
'default-tied-status',
'budget',
'planned-disbursement',
'capital-spend',
'transaction',
'document-link',
'related-activity',
'conditions',
'result',
'legacy-data',
'crs-add',
'fss'
]

def key(s):
    if s in activity_order:
        return activity_order.index(s)
    else:
        return s

def order_activity(l):
    return sorted(l, key=key)
