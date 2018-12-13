import os;
main   = os.path.dirname( os.path.realpath(__file__) );
main   = os.path.join(main, 'data');
images = [os.path.join(main, f) for f in os.listdir(main)]
main   = images[-1];
