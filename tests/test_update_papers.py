"""Offline regressions: synthetic emails, real public ID manifest, no credentials/API."""
import argparse
import json
import os
import sys
import tempfile
import unittest
from contextlib import ExitStack
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import update_papers as u

FIXTURE = json.loads((Path(__file__).parent / 'fixtures/2026-09-28-membership.json').read_text())
EDITION = FIXTURE['edition']
IDS = FIXTURE['complete_ids']
CURATED = FIXTURE['curated_ids']
SUBJECT = f'The Latest NBER Research ({EDITION})'


def message(subject=SUBJECT, ids=IDS, date='Mon, 28 Sep 2026 07:00:00 +0000', body=None):
    result = EmailMessage()
    result['Subject'] = subject
    result['Date'] = date
    result['From'] = 'fixture@example.invalid'
    result.set_content(body if body is not None else '\n'.join(f'https://www.nber.org/papers/{id}' for id in ids))
    return result


def rows(ids):
    return [{'id': id, 'title': 'A research paper', 'title_cn': '经济研究论文', 'abstract': 'Research findings',
             'abstract_cn': '研究发现', 'authors': ['Example Author'], 'url': f'https://www.nber.org/papers/{id}',
             'public_date': EDITION, 'fetched_at': '2026-09-28T07:14:03Z',
             'translation_status': {'title': 'success', 'abstract': 'success'}, 'translation_error': None,
             'translation_prompt_version': u.TRANSLATION_PROMPT_VERSION} for id in ids]


def source(ids=IDS, edition=EDITION):
    return u.EmailSourceResult([{'url': f'https://www.nber.org/papers/{id}'} for id in ids], edition, '', '', len(ids))


class EmailTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_official_43_plus_later_curated_14(self):
        official = message()
        curated = message('本周值得读的论文（NBER + arXiv）· 9月28日', CURATED, date='Tue, 29 Sep 2026 08:00:00 +0000')
        selected = u.select_email_edition(u.newsletter_from_message(curated) + u.newsletter_from_message(official))
        self.assertEqual(u.candidate_ids(selected.candidates), set(IDS))
        self.assertEqual(selected.batch_date, EDITION)

    def test_readonly_imap_scans_all_recent_messages(self):
        box = Mock()
        box.login.return_value = ('OK', [])
        box.select.return_value = ('OK', [])
        box.search.return_value = ('OK', [b'1 2'])
        messages = {b'1': message().as_bytes(), b'2': message('本周值得读的论文（NBER + arXiv）· 9月28日', CURATED).as_bytes()}
        box.fetch.side_effect = lambda id, query: ('OK', [(b'RFC822', messages[id])])
        with patch.object(u, 'imap_config_from_env', return_value=('example.invalid', 993, 'user', 'test')), patch.object(u.imaplib, 'IMAP4_SSL', return_value=box):
            self.assertEqual(u.fetch_email_candidates().link_count, 43)
        box.select.assert_called_once_with('INBOX', readonly=True)
        self.assertTrue(all(call.args[1] == '(BODY.PEEK[])' for call in box.fetch.call_args_list))
        box.logout.assert_called_once()

    def test_forward_date_does_not_change_edition(self):
        self.assertEqual(u.newsletter_from_message(message('Fwd: ' + SUBJECT, date='Fri, 02 Oct 2026 12:00:00 +0000'))[0].batch_date, EDITION)
        self.assertIsNone(u.batch_date_from_email(['NBER research'], 'Fri, 02 Oct 2026 12:00:00 +0000'))

    def test_old_forward_cannot_beat_new_edition(self):
        old = message('Fwd: The Latest NBER Research (2026-09-21)', date='Fri, 02 Oct 2026 12:00:00 +0000')
        selected = u.select_email_edition(u.newsletter_from_message(old) + u.newsletter_from_message(message()))
        self.assertEqual(selected.batch_date, EDITION)

    def test_same_edition_superset_wins_independent_of_arrival(self):
        for inputs in ([source(CURATED), source()], [source(), source(CURATED)]):
            self.assertEqual(u.select_email_edition(inputs).link_count, 43)

    def test_conflicting_same_size_email_copies_fail(self):
        with self.assertRaisesRegex(u.UnsafeBatchError, 'Conflicting paper IDs'):
            u.select_email_edition([source(['w10001']), source(['w10002'])])

    def test_attached_original_does_not_include_wrapper_links(self):
        outer = message('Forwarded newsletter', ['w99999'])
        outer.add_attachment(message())
        result = u.select_email_edition(u.newsletter_from_message(outer))
        self.assertEqual(u.candidate_ids(result.candidates), set(IDS))

    def test_octet_stream_eml_forward(self):
        outer = message('Forwarded newsletter', ['w99999'])
        outer.add_attachment(message().as_bytes(), maintype='application', subtype='octet-stream', filename='newsletter.eml')
        self.assertEqual(u.newsletter_from_message(outer)[0].link_count, 43)

    def test_inline_forward_subject_and_scope(self):
        body = 'https://www.nber.org/papers/w99999\n----- Forwarded message -----\nFrom: fixture@example.invalid\nSubject: ' + SUBJECT + '\n\n' + '\n'.join(f'https://www.nber.org/papers/{id}' for id in IDS)
        result = u.newsletter_from_message(message('Fwd: newsletter', body=body))[0]
        self.assertEqual(u.candidate_ids(result.candidates), set(IDS))
        self.assertEqual(result.batch_date, EDITION)

    def test_html_inline_forward(self):
        outer = message('Fwd: newsletter', body='See HTML')
        outer.add_alternative(f'<p>Subject: <b>{SUBJECT}</b></p><a href="https://www.nber.org/papers/w10001">Paper</a>', subtype='html')
        self.assertEqual(u.newsletter_from_message(outer)[0].batch_date, EDITION)

    def test_inline_forward_excludes_headerless_mime_wrapper(self):
        outer = message('Fwd: newsletter', ['w99999'])
        outer.add_alternative(f'<p>Subject: <b>{SUBJECT}</b></p><a href="https://www.nber.org/papers/w35833">Original paper</a>', subtype='html')
        result = u.newsletter_from_message(outer)[0]
        self.assertEqual(u.candidate_ids(result.candidates), {'w35833'})

    def test_empty_old_email_does_not_block_valid_new_edition(self):
        empty_old = message('The Latest NBER Research (2026-09-21)', body='No valid paper links')
        results = u.newsletter_from_message(empty_old) + u.newsletter_from_message(message())
        with self.assertLogs(level='WARNING') as logs:
            selected = u.select_email_edition(results)
        self.assertEqual(selected.link_count, 43)
        self.assertIn('Ignoring empty older newsletter edition 2026-09-21', '\n'.join(logs.output))

    def test_empty_current_or_newer_copy_still_blocks(self):
        for subject in [SUBJECT, 'The Latest NBER Research (2026-10-05)']:
            with self.subTest(subject=subject), self.assertRaisesRegex(u.UnsafeBatchError, 'empty copy'):
                u.select_email_edition(u.newsletter_from_message(message()) + u.newsletter_from_message(message(subject, body='No valid links')))

    def test_only_empty_candidates_fail_safely(self):
        with self.assertRaisesRegex(u.UnsafeBatchError, 'empty copy'):
            u.select_email_edition(u.newsletter_from_message(message(body='No valid links')))

    def test_imap_scan_skips_empty_old_candidate_after_valid_new_one(self):
        box = Mock()
        box.login.return_value = ('OK', [])
        box.select.return_value = ('OK', [])
        box.search.return_value = ('OK', [b'1 2'])
        messages = {b'1': message('The Latest NBER Research (2026-09-21)', body='No valid links').as_bytes(), b'2': message().as_bytes()}
        box.fetch.side_effect = lambda id, query: ('OK', [(b'RFC822', messages[id])])
        with patch.object(u, 'imap_config_from_env', return_value=('example.invalid', 993, 'user', 'test')), patch.object(u.imaplib, 'IMAP4_SSL', return_value=box), self.assertLogs(level='WARNING'):
            self.assertEqual(u.fetch_email_candidates().link_count, 43)
        box.logout.assert_called_once()

    def test_curated_wrapper_cannot_qualify_via_attached_official_subject(self):
        outer = message('NBER精选', CURATED)
        outer.add_attachment(message())
        self.assertEqual(u.newsletter_from_message(outer), [])

    def test_reject_broad_subjects_and_invalid_dates(self):
        for subject in ['NBER research', 'Latest working papers', SUBJECT + ' picks', 'The Latest NBER Research (2026-02-30)', 'The Latest NBER Research']:
            with self.subTest(subject=subject):
                self.assertEqual(u.newsletter_from_message(message(subject)), [])

    def test_conflicting_inline_date_fails(self):
        with self.assertRaisesRegex(u.UnsafeBatchError, 'disagree'):
            u.newsletter_from_message(message('Fwd: ' + SUBJECT, body='Subject: The Latest NBER Research (2026-09-21)\nhttps://www.nber.org/papers/w10001'))

    def test_configured_sender_allowlist(self):
        with patch.dict(os.environ, {'NBER_EMAIL_ALLOWED_SENDERS': 'approved@example.invalid'}):
            self.assertEqual(u.newsletter_from_message(message()), [])
        with patch.dict(os.environ, {'NBER_EMAIL_ALLOWED_SENDERS': 'fixture@example.invalid'}):
            self.assertEqual(u.newsletter_from_message(message())[0].link_count, 43)

    def test_only_real_nber_links_and_tracking_targets(self):
        links = u.extract_paper_links_from_text('https://other.invalid/papers/w99999 w88888 https://tracking.invalid/?url=https%3A%2F%2Fwww.nber.org%2Fpapers%2Fw10001')
        self.assertEqual(links, ['https://www.nber.org/papers/w10001'])

    def test_publication_date_cannot_relabel_edition(self):
        records = rows(IDS)
        records[-1]['public_date'] = '2026-10-01'
        self.assertEqual(u.refine_to_latest_public_date(records, 'email', EDITION), (records, EDITION))


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.records = rows(IDS)
        self.meta = {'batch_date': EDITION, 'paper_count': 43, 'last_updated': '2026-09-28T07:14:03Z'}
        self.archive = [{'batch_date': EDITION, 'paper_count': 43, 'last_updated': self.meta['last_updated'], 'papers': self.records}]

    def test_curated_loss_rejected(self):
        with self.assertRaisesRegex(u.UnsafeBatchError, 'lose 29'):
            u.validate_batch_coverage(set(CURATED), EDITION, self.records, self.meta, self.archive)

    def test_same_count_id_replacement_rejected(self):
        with self.assertRaisesRegex(u.UnsafeBatchError, 'lose 1'):
            u.validate_batch_coverage(set(IDS[1:] + ['w99999']), EDITION, self.records, self.meta, self.archive)

    def test_archive_is_also_a_baseline(self):
        with self.assertRaisesRegex(u.UnsafeBatchError, 'lose 29'):
            u.validate_batch_coverage(set(CURATED), EDITION, rows(CURATED), self.meta, self.archive)
        with self.assertRaisesRegex(u.UnsafeBatchError, 'lose 29'):
            u.update_archive(self.archive, rows(CURATED), self.meta)

    def test_real_new_week_can_be_smaller(self):
        u.validate_batch_coverage(set(IDS[:3]), '2026-10-05', self.records, self.meta, self.archive)
        result = u.update_archive(self.archive, rows(IDS[:3]), dict(self.meta, batch_date='2026-10-05'))
        self.assertEqual(result[1], self.archive[0])
        self.assertEqual(result[0]['paper_count'], 3)

    def test_stale_edition_rejected(self):
        with self.assertRaisesRegex(u.UnsafeBatchError, 'Stale'):
            u.validate_batch_coverage(set(IDS), '2026-09-21', self.records, self.meta, self.archive)

    def test_duplicate_ids_rejected(self):
        with self.assertRaisesRegex(u.UnsafeBatchError, 'Duplicate'):
            u.record_ids(rows([IDS[0], IDS[0]]))

    def test_bad_stored_data_rejected(self):
        for archive in [None, [{}], [{'batch_date': EDITION, 'papers': None}]]:
            with self.subTest(archive=archive), self.assertRaises(u.UnsafeBatchError):
                u.validate_batch_coverage(set(IDS), EDITION, self.records, self.meta, archive)

    def test_api_fails_closed_without_edition_or_completeness(self):
        with patch.object(u.requests.Session, 'get', side_effect=AssertionError('network must not run')):
            with self.assertRaisesRegex(u.UnsafeBatchError, 'complete membership'):
                u.fetch_api_candidates()


class RunTests(unittest.TestCase):
    def setUp(self):
        CoverageTests.setUp(self)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.paths = {}
        for name, value in [('PAPERS_PATH', self.records), ('META_PATH', self.meta), ('ARCHIVE_PATH', self.archive), ('CACHE_PATH', {}), ('AUDIT_PATH', 'original audit')]:
            path = Path(self.temp.name) / name
            path.write_text(json.dumps(value))
            self.paths[name] = path
            self.stack.enter_context(patch.object(u, name, path))
        self.before = {path: path.read_bytes() for path in self.paths.values()}
        self.args = argparse.Namespace(test_email_login=False, audit_translations=False, require_api_key=False, dry_run=False, source='auto', email_lookback=100, per_page=50, model='test', translation_workers=2, skip_audit_report=False, audit_output=str(self.paths['AUDIT_PATH']))
        self.stack.enter_context(patch.dict(os.environ, {'KIMI_API_KEY': 'test-not-a-real-key'}, clear=True))
        self.stack.enter_context(patch.object(u, 'parse_args', return_value=self.args))
        self.stack.enter_context(patch.object(u, 'load_local_env'))
        self.stack.enter_context(patch.object(u, 'has_imap_config', return_value=True))
        self.stack.enter_context(patch.object(u, 'build_session'))
        self.mail = self.stack.enter_context(patch.object(u, 'fetch_email_candidates', return_value=source()))
        self.build = self.stack.enter_context(patch.object(u, 'build_records', side_effect=lambda session, candidates, stamp: (rows([u.paper_id_from_url(p['url'], p) for p in candidates]), [])))
        self.translate = self.stack.enter_context(patch.object(u, 'translate_records', return_value={}))
        self.client = self.stack.enter_context(patch.object(u, 'OpenAI', side_effect=AssertionError('No paid API calls')))

    def assert_unchanged(self):
        self.assertEqual(self.before, {path: path.read_bytes() for path in self.paths.values()})

    def test_loss_gate_before_details_translation_or_writes(self):
        self.mail.return_value = source(CURATED)
        with self.assertRaisesRegex(u.UnsafeBatchError, 'lose 29'):
            u.run()
        self.build.assert_not_called()
        self.translate.assert_not_called()
        self.client.assert_not_called()
        self.assert_unchanged()

    def test_detail_processing_loss_is_rechecked(self):
        self.build.side_effect = None
        self.build.return_value = (rows(CURATED), [])
        with self.assertRaisesRegex(u.UnsafeBatchError, 'lose 29'):
            u.run()
        self.translate.assert_not_called()
        self.assert_unchanged()

    def test_same_count_id_replacement_gate_before_translation(self):
        self.mail.return_value = source(IDS[1:] + ['w99999'])
        with self.assertRaisesRegex(u.UnsafeBatchError, 'lose 1'):
            u.run()
        self.translate.assert_not_called()
        self.assert_unchanged()

    def test_idempotent_repeat_preserves_all_bytes(self):
        self.assertEqual(u.run(), 0)
        self.assertEqual(u.run(), 0)
        self.translate.assert_not_called()
        self.client.assert_not_called()
        self.assert_unchanged()

    def test_new_smaller_week_writes_consistent_snapshot(self):
        self.mail.return_value = source(IDS[:3], '2026-10-05')
        self.assertEqual(u.run(), 0)
        meta = json.loads(self.paths['META_PATH'].read_text())
        records = json.loads(self.paths['PAPERS_PATH'].read_text())
        archive = json.loads(self.paths['ARCHIVE_PATH'].read_text())
        self.assertEqual((meta['batch_date'], meta['paper_count']), ('2026-10-05', 3))
        self.assertEqual(archive[0]['papers'], records)
        self.assertEqual(archive[1], self.archive[0])
        self.translate.reset_mock()
        self.assertEqual(u.run(), 0)
        self.translate.assert_not_called()

    def test_auto_mode_cannot_bypass_unsafe_email(self):
        self.mail.side_effect = u.UnsafeBatchError('Conflicting edition')
        with patch.object(u, 'fetch_api_candidates') as fallback, self.assertRaises(u.UnsafeBatchError):
            u.run()
        fallback.assert_not_called()
        self.translate.assert_not_called()
        self.assert_unchanged()

    def test_missing_email_api_fallback_fails_before_writes(self):
        self.mail.side_effect = RuntimeError('No recognized newsletter')
        with self.assertRaisesRegex(u.UnsafeBatchError, 'complete membership'):
            u.run()
        self.translate.assert_not_called()
        self.assert_unchanged()

    def test_write_failure_restores_whole_snapshot(self):
        self.mail.return_value = source(IDS[:3], '2026-10-05')
        real_replace = os.replace
        count = 0
        def failing_replace(src, dst):
            nonlocal count
            count += 1
            if count == 4:
                raise OSError('injected disk failure')
            return real_replace(src, dst)
        with patch.object(u.os, 'replace', side_effect=failing_replace), self.assertRaisesRegex(OSError, 'injected'):
            u.run()
        self.assert_unchanged()
        self.assertEqual(set(Path(self.temp.name).iterdir()), set(self.paths.values()))

    def test_staging_failure_keeps_all_originals(self):
        with patch.object(u.os, 'fsync', side_effect=OSError('disk full')), self.assertRaisesRegex(OSError, 'disk full'):
            u.write_snapshot({path: 'new value' for path in self.paths.values()})
        self.assert_unchanged()
        self.assertEqual(set(Path(self.temp.name).iterdir()), set(self.paths.values()))


class RestoredDataTests(unittest.TestCase):
    def test_historical_edition_is_complete_and_translated(self):
        archive = json.loads((u.DATA_DIR / 'archive.json').read_text())
        entries = [entry for entry in archive if entry['batch_date'] == EDITION]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry['paper_count'], 43)
        self.assertEqual([record['id'] for record in entry['papers']], IDS)
        self.assertTrue(set(CURATED) < set(IDS))
        self.assertEqual(sum(status == 'success' for record in entry['papers'] for status in record['translation_status'].values()), 86)
        meta = json.loads((u.DATA_DIR / 'update-meta.json').read_text())
        if meta['batch_date'] == EDITION:
            self.assertEqual(json.loads((u.DATA_DIR / 'papers.json').read_text()), entry['papers'])
            self.assertEqual(meta['paper_count'], 43)
            self.assertEqual(meta['last_updated'], entry['last_updated'])


if __name__ == '__main__':
    unittest.main()
