import json, sys
from app import create_app, db
from app.models import InspirationItem, Opportunity, StudyMaterial, Notification

app = create_app()
app.config['TESTING'] = True
failures = []

with app.app_context():
    db.create_all()

with app.test_client() as c:
    with c.session_transaction() as s:
        s['_user_id'] = '1'; s['_fresh'] = True

    def chk(label, path, method='GET', data=None, ct=None, expected=200):
        try:
            if method == 'GET':
                r = c.get(path)
            else:
                kw = {'data': data} if ct is None else {'data': data, 'content_type': ct}
                r = c.post(path, **kw)
            ok = r.status_code == expected
            sym = 'PASS' if ok else 'FAIL'
            if not ok: failures.append('%s: got %d' % (label, r.status_code))
            print('%s  %-30s -> %d' % (sym, label, r.status_code))
            return r
        except Exception as e:
            failures.append('%s: EXCEPTION %s' % (label, e))
            print('FAIL  %s: %s' % (label, e))
            return None

    # All pages
    for label, path in [
        ('landing',         '/'),
        ('dashboard',       '/dashboard/'),
        ('opportunities',   '/opportunities/'),
        ('inspiration',     '/inspiration/'),
        ('insp/new',        '/inspiration/new'),
        ('insp/inbox',      '/inspiration/inbox'),
        ('insp/agent-feed', '/inspiration/agent-feed'),
        ('insp/search',     '/inspiration/search?q=marketing'),
        ('profiles',        '/profiles/'),
        ('skills',          '/skills/'),
        ('applications',    '/applications/'),
        ('library',         '/library/'),
        ('backup',          '/backup/'),
        ('projects',        '/projects/'),
        ('notifications',   '/notifications/'),
    ]:
        chk(label, path)

    # Analyze endpoint
    def analyze(url):
        r = c.post('/inspiration/analyze',
                   data=json.dumps({'url': url}),
                   content_type='application/json')
        return r.status_code, json.loads(r.data)

    tests = [
        ('instagram_reel',   'https://www.instagram.com/reel/C8Xyz123/',            'Instagram',  None),
        ('instagram_profile','https://www.instagram.com/iamankurwarikoo/',           'Instagram',  None),
        ('youtube',          'https://www.youtube.com/@TedTalks/videos',             'YouTube',    None),
        ('linkedin_profile', 'https://www.linkedin.com/in/satya-nadella/',           'LinkedIn',   None),
        ('internshala',      'https://internshala.com/internship/marketing/9999',    'Job Portal', 'Internship'),
        ('unstop',           'https://unstop.com/internships/business-analyst',      'Job Portal', 'Internship'),
        ('coursera',         'https://www.coursera.org/learn/machine-learning',      'Course',     'Course'),
        ('udemy',            'https://www.udemy.com/course/python-bootcamp/',        'Course',     'Course'),
        ('hbr_article',      'https://hbr.org/2024/01/how-to-build-career',         'Article',    'Business Strategy'),
        ('twitter_x',        'https://x.com/paulg/status/123456',                   'Twitter',    None),
        ('reddit',           'https://reddit.com/r/marketing/comments/abc',         'Reddit',     None),
        ('naukri',           'https://www.naukri.com/mba-jobs-in-bangalore',        'Job Portal', 'Job Opportunity'),
        ('medium',           'https://medium.com/@author/consulting-career',        'Article',    None),
    ]

    for name, url, exp_plat, exp_cat in tests:
        code, d = analyze(url)
        plat_ok = d.get('platform') == exp_plat
        cat_ok  = (exp_cat is None) or (d.get('category') == exp_cat)
        tags_ok = bool(d.get('tags'))
        conf_ok = 'confidence_score' in d
        ok = code == 200 and plat_ok and cat_ok and tags_ok and conf_ok
        sym = 'PASS' if ok else 'FAIL'
        issues = []
        if not plat_ok: issues.append('platform=%s want %s' % (d.get('platform'), exp_plat))
        if not cat_ok:  issues.append('cat=%s want %s' % (d.get('category'), exp_cat))
        if not tags_ok: issues.append('no tags')
        if issues: failures.append('analyze/%s: %s' % (name, issues))
        print('%s  analyze/%-20s plat=%-12s cat=%-22s route=%-15s conf=%.2f' % (
            sym, name, d.get('platform','?'), d.get('category','?'),
            d.get('auto_route_target','-'), d.get('confidence_score', 0)))

    # Auto-routing verification
    with app.app_context():
        before_opp = Opportunity.query.filter_by(user_id=1).count()
        before_lib = StudyMaterial.query.filter_by(user_id=1).count()

    import time; ts = str(int(time.time()))
    c.post('/inspiration/new', data={
        'link': 'https://internshala.com/internship/finance-intern-delhi/' + ts,
        'platform': 'Job Portal', 'category': 'Internship',
        'title': 'Finance Intern at XYZ Corp ' + ts, 'is_actionable': 'on',
        'urgency': 'High', 'career_relevance': 'High',
        'priority': 'High', 'ai_analyzed': '1', 'confidence_score': '0.8',
    }, follow_redirects=True)

    c.post('/inspiration/new', data={
        'link': 'https://www.coursera.org/learn/python-bootcamp-' + ts,
        'platform': 'Course', 'category': 'Course',
        'title': 'Python Bootcamp on Coursera ' + ts, 'ai_analyzed': '1',
        'confidence_score': '0.75',
    }, follow_redirects=True)

    with app.app_context():
        new_opp = Opportunity.query.filter_by(user_id=1).count() - before_opp
        new_lib = StudyMaterial.query.filter_by(user_id=1).count() - before_lib
        new_notif = Notification.query.filter_by(user_id=1, is_read=False).count()

    for label, val, expected_min in [
        ('auto_route/internship -> Opportunity', new_opp, 1),
        ('auto_route/course -> StudyMaterial', new_lib, 1),
    ]:
        ok = val >= expected_min
        sym = 'PASS' if ok else 'FAIL'
        if not ok: failures.append('%s: got %d' % (label, val))
        print('%s  %-42s -> %d new records' % (sym, label, val))

    # Share target
    r = c.get('/inspiration/share?url=https://internshala.com/internship/data-analyst/777')
    ok = r.status_code in (200, 302)
    sym = 'PASS' if ok else 'FAIL'
    if not ok: failures.append('share_target: %d' % r.status_code)
    print('%s  %-42s -> %d' % (sym, 'share_target', r.status_code))

    # Semantic search
    r = c.get('/inspiration/search?q=internship')
    ok = r.status_code == 200
    sym = 'PASS' if ok else 'FAIL'
    if not ok: failures.append('semantic_search: %d' % r.status_code)
    print('%s  %-42s -> %d' % (sym, 'semantic_search', r.status_code))

    # Daily brief
    try:
        from app.agent.brief import generate_daily_brief
        with app.app_context():
            brief = generate_daily_brief(1)
        required = ['new_opportunities','expiring','active_apps','urgent_inspirations',
                    'revisit_due','lagging_skills','top_categories','forgotten',
                    'week_inspirations','week_opportunities','next_actions']
        missing = [k for k in required if k not in brief]
        ok = not missing
        sym = 'PASS' if ok else 'FAIL'
        if not ok: failures.append('daily_brief missing keys: %s' % missing)
        print('%s  %-42s keys=%d' % (sym, 'daily_brief', len(brief)))
    except Exception as e:
        failures.append('daily_brief: %s' % e)
        print('FAIL  daily_brief: %s' % e)

    # PWA manifest accessible
    r = c.get('/static/manifest.json')
    ok = r.status_code == 200
    sym = 'PASS' if ok else 'FAIL'
    if not ok: failures.append('pwa_manifest: %d' % r.status_code)
    print('%s  %-42s -> %d' % (sym, 'pwa_manifest', r.status_code))

    # SW accessible
    r = c.get('/static/sw.js')
    ok = r.status_code == 200
    sym = 'PASS' if ok else 'FAIL'
    if not ok: failures.append('service_worker: %d' % r.status_code)
    print('%s  %-42s -> %d' % (sym, 'service_worker', r.status_code))

    print()
    print('=== %d failure(s) ===' % len(failures))
    for f in failures:
        print(' -', f)

sys.exit(0 if not failures else 1)
