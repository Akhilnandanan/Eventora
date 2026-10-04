\# Eventora — Demo Account Credentials



These accounts are created by running:python manage.py seed\_demo\_data

All demo accounts use the same password: \*\*demo1234\*\*



\## Vendors

| Username | Business |

|---|---|

| demo\_vendor1 | Shutter Stories Photography |

| demo\_vendor2 | Royal Feast Catering |

| demo\_vendor3 | Dream Day Events |

| demo\_vendor4 | BeatDrop DJ Services |

| demo\_vendor5 | Bloom \& Petal Decor |

| demo\_vendor6 | Glow Studio Makeup |



\## Customers

| Username | Name |

|---|---|

| demo\_customer1 | Aditi Sharma |

| demo\_customer2 | Rohan Mehta |

| demo\_customer3 | Priya Nair |

| demo\_customer4 | Karan Kapoor |



\## Admin

Use whichever superuser account you created earlier with `createsuperuser`.



\## Resetting demo data

To wipe previously seeded demo accounts and reseed fresh:python manage.py seed\_demo\_data --reset

This only removes accounts whose username starts with `demo\_` — it will never touch your own manually created accounts.

