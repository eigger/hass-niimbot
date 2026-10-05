# Preview on a dashboard

A `niimbot.print` action with `preview: true` updates the printer's **Last Label Made** image entity without printing. Add that entity to a dashboard to review the latest rendered label.

```yaml
type: picture-entity
entity: image.<your_printer>_last_label_made
show_name: false
show_state: false
camera_view: auto
```

For an action you can run while editing a label, use [`preview.yaml`](../preview.yaml). The action also returns the rendered PNG as `image` when called with `response_variable` from a script.
