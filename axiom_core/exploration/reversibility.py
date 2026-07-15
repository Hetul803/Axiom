def score(action, legal):
    inv={"up":"down","down":"up","left":"right","right":"left","w":"s","s":"w","a":"d","d":"a"}; return 1.0 if inv.get(str(action)) in {str(a) for a in legal} else .45
