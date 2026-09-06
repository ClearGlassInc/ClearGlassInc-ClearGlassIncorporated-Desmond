Homepage loader cleanup status

The homepage has two loader paths:

1. The inline primary loader inside index.html.
2. A first-visit redirect gate in index.html that sends users to cg-loader.html.

The crimson/red loading experience is cg-loader.html. The required homepage-only fix is to remove the redirect gate from index.html and preserve the inline primary loader exactly as-is.

Target file: index.html
Target removal: the first script block in the head that contains cg-loader.html?next=index.html
Preserve: the inline #cg-loader markup, styles, and boot controller.
