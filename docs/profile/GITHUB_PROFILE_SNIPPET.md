# GitHub Profile Badge Snippet

Use this file when you want to show your earned lab badge in your GitHub profile README.

Recommended destination:

- `https://github.com/Subash107/Subash107`
- Edit the profile repository `README.md`

## Recommended Snippet

This version is the most reliable on GitHub because it embeds the badge image from the raw file URL and links to the rendered award record in the lab repository.

```md
## Lab Certifications

[![Subash completion badge](https://raw.githubusercontent.com/Subash107/ParrotOS/main/achievements/badges/subash107-full-lab-completion.svg)](https://github.com/Subash107/ParrotOS/blob/main/achievements/records/subash107-full-lab-completion.md)
```

## Showcase Version

Use this if you want the badge to stand out more in your profile README.

```html
<h2>Lab Certifications</h2>
<p>
  <a href="https://github.com/Subash107/ParrotOS/blob/main/achievements/records/subash107-full-lab-completion.md">
    <img
      src="https://raw.githubusercontent.com/Subash107/ParrotOS/main/achievements/badges/subash107-full-lab-completion.svg"
      alt="Subash - Full Lab Completion badge"
      width="420"
    />
  </a>
</p>
<p>
  Earned by completing the Acme DevSecOps Bug Bounty Simulation Lab, including recon,
  exploitation validation, and reporting.
</p>
```

## Compact Text Link

Use this if you want a simple text-first profile.

```md
- [Acme DevSecOps Bug Bounty Simulation Lab - Full Lab Completion](https://github.com/Subash107/ParrotOS/blob/main/achievements/records/subash107-full-lab-completion.md)
```

## Optional Certificate Link

If you want to link directly to the generated certificate file, use:

- `https://github.com/Subash107/ParrotOS/blob/main/achievements/certificates/subash107-full-lab-completion.html`

GitHub shows HTML files as repository content, so the award record link is usually the nicer public-facing destination.
