;;; Directory Local Variables            -*- no-byte-compile: t -*-
;;; For more information see (info "(emacs) Directory Variables")

((nil . ((eglot-workspace-configuration . (:basedpyright (:python (:pythonPath "./venv/bin/python"))))
	 (projectile-project-test-cmd . "hatch run test")
	 (projectile-tasks . (("doc-build" . "hatch run docs")
			      ("doc-serve" . "hatch run docserve"))))))
