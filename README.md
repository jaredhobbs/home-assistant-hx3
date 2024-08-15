# Hx 3 Thermostat

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[![Community Forum][forum-shield]][forum]

_Component to integrate with [Hx 3 thermostats][hx3]._

![example][exampleimg]

## Installation

1. Using your tool of choice, open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `hx3`.
4. Download _all_ the files from the `custom_components/hx3/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Hx 3 Thermostat"

## Create new user token

Before you can use this integration, you'll need to have already setup the
Hx mobile app. Open the mobile app and navigate to... 
iOS: Settings->Multiple users.
Android: Settings->Manage account->Share account

Click the "Share code" button and copy the message that the app generates. It
should look something like this:

```text
I'm using the Hx Thermostat app to control our thermostat.
Once you’ve downloaded the app, you can tap this link to share my account:
https://hx.kraftful.app/signIn/<email address>/<token>

Or you can use my email to sign in:
<email address>

And enter this code when prompted:
<token>

This code will only work for a week. Let me know if you want me to send a new one.
```

Make note of the `<email address>` and `<token>` from the text.

## Configuration is done in the UI

1. Email: enter the email from `<email address>` above
2. Token: enter the token from `<token>` above
3. Access token: leave this field blank
4. Refresh token: leave this field blank
5. TTL: leave this field as 0
6. Last refresh: leave this field as 0

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

[hx3]: https://devauthor.jci.com/residential-equipment/residential-thermostats/hx3_touch_screen_thermostat_ds
[buymecoffee]: https://www.buymeacoffee.com/jaredhobbs
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/custom-components/blueprint.svg?style=for-the-badge
[commits]: https://github.com/jaredhobbs/home-assistant-hx3/commits/master
[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[exampleimg]: hx3.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/custom-components/blueprint.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Jared%20Hobbs%20%40jaredhobbs-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/custom-components/blueprint.svg?style=for-the-badge
[releases]: https://github.com/jaredhobbs/home-assistant-hx3/releases
