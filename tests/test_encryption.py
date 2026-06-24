"""Tests for PDF encryption (pdf_user_password / pdf_owner_password)."""

import io

import pytest

from .testing_utils import FakeHTML, assert_no_logs

pikepdf = pytest.importorskip('pikepdf')

HTML = '<h1>Secret</h1><p>Confidential content</p>'


@assert_no_logs
def test_no_encryption_by_default():
    pdf = FakeHTML(string=HTML).write_pdf()
    assert b'/Encrypt' not in pdf
    # Opens without any password.
    document = pikepdf.open(io.BytesIO(pdf))
    assert not document.is_encrypted


@assert_no_logs
def test_user_password():
    pdf = FakeHTML(string=HTML).write_pdf(pdf_user_password='open-sesame')
    assert b'/Encrypt' in pdf
    # Cannot open without the password.
    with pytest.raises(pikepdf.PasswordError):
        pikepdf.open(io.BytesIO(pdf))
    # Opens with the user password.
    document = pikepdf.open(io.BytesIO(pdf), password='open-sesame')
    assert document.is_encrypted


@assert_no_logs
def test_owner_password_permissions():
    # Empty user password opens without a prompt; permissions are enforced.
    pdf = FakeHTML(string=HTML).write_pdf(
        pdf_owner_password='owner', pdf_permissions=-44)
    document = pikepdf.open(io.BytesIO(pdf))
    assert document.is_encrypted
    assert not document.allow.modify_other
    # Owner password grants access too.
    assert pikepdf.open(io.BytesIO(pdf), password='owner').is_encrypted


@assert_no_logs
def test_wrong_password_rejected():
    pdf = FakeHTML(string=HTML).write_pdf(pdf_user_password='right')
    with pytest.raises(pikepdf.PasswordError):
        pikepdf.open(io.BytesIO(pdf), password='wrong')


@assert_no_logs
def test_aes_encryption():
    pdf = FakeHTML(string=HTML).write_pdf(
        pdf_user_password='aes-pw', pdf_encryption_method='aes')
    assert b'/AESV2' in pdf
    with pytest.raises(pikepdf.PasswordError):
        pikepdf.open(io.BytesIO(pdf))
    document = pikepdf.open(io.BytesIO(pdf), password='aes-pw')
    assert document.is_encrypted
